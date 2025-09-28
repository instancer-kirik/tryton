#!/bin/bash
set -e

# Pre-deployment Security and Readiness Check for Tryton Railway
# This script performs comprehensive checks before production deployment

echo "🚀 TRYTON RAILWAY PRE-DEPLOYMENT CHECK"
echo "======================================"
echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo "Environment: ${RAILWAY_ENVIRONMENT:-local}"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Helper functions
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((CHECKS_PASSED++))
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    ((CHECKS_FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((CHECKS_WARNING++))
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_command_exists() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# 1. ENVIRONMENT CHECK
echo "1. CHECKING DEVELOPMENT ENVIRONMENT"
echo "-----------------------------------"

if check_command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    print_success "Python 3 available: $PYTHON_VERSION"
else
    print_error "Python 3 is not available"
fi

if check_command_exists git; then
    GIT_VERSION=$(git --version)
    print_success "Git available: $GIT_VERSION"
else
    print_error "Git is not available"
fi

if check_command_exists railway; then
    RAILWAY_VERSION=$(railway --version 2>&1 || echo "Railway CLI installed")
    print_success "Railway CLI available: $RAILWAY_VERSION"
else
    print_warning "Railway CLI not available (optional for manual deployment)"
fi

echo ""

# 2. FILE STRUCTURE CHECK
echo "2. CHECKING REQUIRED FILES"
echo "--------------------------"

REQUIRED_FILES=(
    "Dockerfile"
    "railway.toml"
    "requirements.txt"
    "wsgi.py"
    "create_config.py"
    "start_server.sh"
    "validate_env.py"
    "SECURITY.md"
    "RAILWAY_DEPLOYMENT.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        print_success "Required file exists: $file"
    else
        print_error "Missing required file: $file"
    fi
done

# Check file permissions
if [[ -f "start_server.sh" ]]; then
    if [[ -x "start_server.sh" ]]; then
        print_success "start_server.sh is executable"
    else
        print_warning "start_server.sh is not executable (will be fixed during deployment)"
    fi
fi

echo ""

# 3. PYTHON DEPENDENCIES CHECK
echo "3. CHECKING PYTHON DEPENDENCIES"
echo "-------------------------------"

if [[ -f "requirements.txt" ]]; then
    print_info "Checking requirements.txt syntax..."

    if python3 -m pip install --dry-run -r requirements.txt &>/dev/null; then
        print_success "requirements.txt syntax is valid"
    else
        print_error "requirements.txt has syntax errors or invalid packages"
    fi

    # Check for security-sensitive packages
    if grep -q "trytond" requirements.txt; then
        print_success "Tryton core package found in requirements"
    else
        print_error "Tryton core package (trytond) not found in requirements"
    fi

    if grep -q "psycopg2" requirements.txt; then
        print_success "PostgreSQL driver found in requirements"
    else
        print_error "PostgreSQL driver (psycopg2-binary) not found in requirements"
    fi

    if grep -q "gunicorn" requirements.txt; then
        print_success "Gunicorn web server found in requirements"
    else
        print_error "Gunicorn web server not found in requirements"
    fi
else
    print_error "requirements.txt not found"
fi

echo ""

# 4. CONFIGURATION FILES CHECK
echo "4. CHECKING CONFIGURATION"
echo "-------------------------"

if [[ -f "railway.toml" ]]; then
    print_success "railway.toml configuration found"

    # Check for security settings in railway.toml
    if grep -q "healthcheckPath" railway.toml; then
        print_success "Health check endpoint configured"
    else
        print_warning "No health check endpoint in railway.toml"
    fi

    if grep -q "DOCKERFILE" railway.toml; then
        print_success "Docker build configuration found"
    else
        print_warning "Docker build not explicitly configured"
    fi
else
    print_error "railway.toml configuration not found"
fi

if [[ -f "Dockerfile" ]]; then
    print_success "Dockerfile found"

    # Check for security best practices in Dockerfile
    if grep -q "USER" Dockerfile; then
        print_success "Non-root user configured in Dockerfile"
    else
        print_warning "Dockerfile might run as root (security concern)"
    fi

    if grep -q "COPY.*requirements.txt" Dockerfile; then
        print_success "Requirements properly copied in Dockerfile"
    else
        print_warning "Requirements handling in Dockerfile should be checked"
    fi
else
    print_error "Dockerfile not found"
fi

echo ""

# 5. SECURITY FILES CHECK
echo "5. CHECKING SECURITY DOCUMENTATION"
echo "----------------------------------"

if [[ -f "SECURITY.md" ]]; then
    print_success "Security documentation exists"

    # Check if security doc is comprehensive
    if grep -q "Environment Variables" SECURITY.md; then
        print_success "Security doc covers environment variables"
    fi

    if grep -q "Password" SECURITY.md; then
        print_success "Security doc covers password security"
    fi
else
    print_warning "SECURITY.md documentation missing"
fi

if [[ -f "validate_env.py" ]]; then
    print_success "Environment validation script exists"

    # Test the validation script syntax
    if python3 -m py_compile validate_env.py; then
        print_success "Environment validation script syntax is valid"
    else
        print_error "Environment validation script has syntax errors"
    fi
else
    print_error "Environment validation script missing"
fi

echo ""

# 6. GIT REPOSITORY CHECK
echo "6. CHECKING GIT REPOSITORY"
echo "-------------------------"

if [[ -d ".git" ]]; then
    print_success "Git repository initialized"

    # Check for uncommitted changes
    if git diff-index --quiet HEAD --; then
        print_success "No uncommitted changes"
    else
        print_warning "Uncommitted changes detected - commit before deployment"
    fi

    # Check for untracked files
    UNTRACKED=$(git ls-files --others --exclude-standard)
    if [[ -z "$UNTRACKED" ]]; then
        print_success "No untracked files"
    else
        print_warning "Untracked files found: $UNTRACKED"
    fi

    # Check current branch
    CURRENT_BRANCH=$(git branch --show-current)
    print_info "Current branch: $CURRENT_BRANCH"

    # Check for security-sensitive files in git
    if git ls-files | grep -E "\.(env|key|pem|p12)$" > /dev/null; then
        print_error "Sensitive files detected in git repository"
    else
        print_success "No sensitive files in git repository"
    fi

else
    print_warning "Not a git repository (manual deployment only)"
fi

echo ""

# 7. ENVIRONMENT VARIABLES VALIDATION
echo "7. ENVIRONMENT VARIABLES VALIDATION"
echo "-----------------------------------"

if [[ -f "validate_env.py" ]]; then
    print_info "Running environment validation script..."

    # Run the validation script and capture result
    if python3 validate_env.py > /tmp/env_validation.log 2>&1; then
        print_success "Environment variables validation passed"
    else
        print_error "Environment variables validation failed"
        print_info "Check the output above or run 'python3 validate_env.py' manually"
    fi
else
    print_warning "Environment validation script not available"

    # Basic environment checks
    REQUIRED_ENV_VARS=("DATABASE_URL" "ADMIN_PASSWORD" "SECRET_KEY" "FRONTEND_URL" "CORS_ORIGINS")

    for var in "${REQUIRED_ENV_VARS[@]}"; do
        if [[ -n "${!var}" ]]; then
            print_success "Environment variable set: $var"
        else
            print_warning "Environment variable not set: $var (required for deployment)"
        fi
    done
fi

echo ""

# 8. SECURITY CHECKLIST
echo "8. SECURITY CHECKLIST"
echo "--------------------"

# Check for common security issues
if [[ -n "$ADMIN_PASSWORD" ]]; then
    if [[ ${#ADMIN_PASSWORD} -ge 12 ]]; then
        print_success "ADMIN_PASSWORD length is adequate (≥12 characters)"
    else
        print_error "ADMIN_PASSWORD is too short (<12 characters)"
    fi

    # Check for common weak passwords
    WEAK_PASSWORDS=("admin" "password" "123456" "root" "tryton")
    for weak in "${WEAK_PASSWORDS[@]}"; do
        if [[ "${ADMIN_PASSWORD,,}" == *"${weak,,}"* ]]; then
            print_error "ADMIN_PASSWORD contains weak pattern: $weak"
            break
        fi
    done
else
    print_warning "ADMIN_PASSWORD not set in current environment"
fi

if [[ -n "$SECRET_KEY" ]]; then
    if [[ ${#SECRET_KEY} -ge 32 ]]; then
        print_success "SECRET_KEY length is adequate (≥32 characters)"
    else
        print_error "SECRET_KEY is too short (<32 characters)"
    fi
else
    print_warning "SECRET_KEY not set in current environment"
fi

if [[ -n "$CORS_ORIGINS" ]]; then
    if [[ "$CORS_ORIGINS" == *"*"* ]]; then
        print_error "CORS_ORIGINS contains wildcard (*) - security risk"
    else
        print_success "CORS_ORIGINS does not contain wildcards"
    fi

    if [[ "$CORS_ORIGINS" == *"http://"* ]] && [[ "$CORS_ORIGINS" != *"localhost"* ]]; then
        print_warning "CORS_ORIGINS contains HTTP URLs (should use HTTPS in production)"
    fi
else
    print_warning "CORS_ORIGINS not set in current environment"
fi

echo ""

# 9. FINAL SUMMARY
echo "DEPLOYMENT READINESS SUMMARY"
echo "============================="
echo -e "Checks passed:  ${GREEN}$CHECKS_PASSED${NC}"
echo -e "Checks failed:  ${RED}$CHECKS_FAILED${NC}"
echo -e "Warnings:       ${YELLOW}$CHECKS_WARNING${NC}"
echo ""

# Determine deployment readiness
if [[ $CHECKS_FAILED -eq 0 ]]; then
    if [[ $CHECKS_WARNING -eq 0 ]]; then
        echo -e "${GREEN}🎉 READY FOR DEPLOYMENT${NC}"
        echo "All checks passed! Your Tryton application is ready for Railway deployment."
        echo ""
        echo "Next steps:"
        echo "1. Commit and push your changes to GitHub"
        echo "2. Deploy via Railway dashboard or CLI"
        echo "3. Run post-deployment health checks"
        echo "4. Test DivvyQueue integration"
    else
        echo -e "${YELLOW}⚠️  READY WITH WARNINGS${NC}"
        echo "Deployment is possible but please review the warnings above."
        echo "Consider addressing warnings for better security and reliability."
        echo ""
        echo "Next steps:"
        echo "1. Review and address warnings if possible"
        echo "2. Commit and push your changes to GitHub"
        echo "3. Deploy via Railway dashboard or CLI"
        echo "4. Monitor deployment logs carefully"
    fi

    echo ""
    echo "Deployment commands:"
    echo "  railway up                    # Deploy via CLI"
    echo "  git push origin main          # Deploy via GitHub Actions"

    exit 0
else
    echo -e "${RED}❌ NOT READY FOR DEPLOYMENT${NC}"
    echo "Please fix the errors listed above before deploying to production."
    echo ""
    echo "Common fixes:"
    echo "1. Set missing environment variables in Railway"
    echo "2. Fix file permissions: chmod +x start_server.sh"
    echo "3. Commit changes: git add . && git commit -m 'Fix deployment issues'"
    echo "4. Run validation script: python3 validate_env.py"
    echo ""
    echo "Re-run this script after making fixes:"
    echo "  bash pre_deploy_check.sh"

    exit 1
fi
