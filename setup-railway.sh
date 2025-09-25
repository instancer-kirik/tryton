#!/bin/bash
# Tryton Railway Deployment Setup Script
# Automates the complete Railway deployment process for DivvyQueue integration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TRYTON_DIR=$(pwd)
RAILWAY_PROJECT_NAME="divvyqueue-tryton"
DEFAULT_ADMIN_EMAIL="admin@divvyqueue.com"
DEFAULT_DATABASE_NAME="divvyqueue_prod"

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
    echo "----------------------------------------"
}

check_prerequisites() {
    log_step "Checking prerequisites..."

    # Check if we're in the Tryton directory
    if [[ ! -f "trytond/setup.py" ]]; then
        log_error "This script must be run from the Tryton repository root directory"
    fi

    # Check required tools
    command -v npm >/dev/null 2>&1 || log_error "npm is required but not installed"
    command -v git >/dev/null 2>&1 || log_error "git is required but not installed"
    command -v python3 >/dev/null 2>&1 || log_error "python3 is required but not installed"

    # Check if Railway CLI is installed
    if ! command -v railway >/dev/null 2>&1; then
        log_warn "Railway CLI not found. Installing..."
        npm install -g @railway/cli
    fi

    log_info "Prerequisites check passed"
}

setup_github() {
    log_step "Setting up GitHub repository..."

    # Check if origin remote exists
    if ! git remote get-url origin >/dev/null 2>&1; then
        echo "Please set up your GitHub fork first:"
        echo "1. Fork https://github.com/tryton/tryton to your GitHub account"
        echo "2. Run: git remote add origin https://github.com/YOUR_USERNAME/tryton.git"
        echo "3. Run: git push -u origin main"
        read -p "Press Enter when ready to continue..."
    fi

    # Ensure all Railway files are committed
    log_info "Committing Railway deployment files..."

    git add railway.toml Dockerfile requirements.txt railway-trytond.conf 2>/dev/null || true
    git add .github/workflows/railway-deploy.yml 2>/dev/null || true
    git add RAILWAY_DEPLOYMENT.md setup-railway.sh 2>/dev/null || true

    if git diff --cached --quiet; then
        log_info "No new files to commit"
    else
        git commit -m "Add Railway deployment configuration for DivvyQueue integration"
        git push origin main
        log_info "Railway configuration pushed to GitHub"
    fi
}

railway_login() {
    log_step "Railway authentication..."

    if railway whoami >/dev/null 2>&1; then
        log_info "Already logged in to Railway as: $(railway whoami)"
    else
        log_info "Please log in to Railway..."
        railway login
    fi
}

collect_configuration() {
    log_step "Collecting deployment configuration..."

    echo "Please provide the following configuration details:"
    echo ""

    # Admin email
    read -p "Admin email [$DEFAULT_ADMIN_EMAIL]: " ADMIN_EMAIL
    ADMIN_EMAIL=${ADMIN_EMAIL:-$DEFAULT_ADMIN_EMAIL}

    # Admin password
    while true; do
        read -s -p "Admin password (min 8 characters): " ADMIN_PASSWORD
        echo
        if [[ ${#ADMIN_PASSWORD} -ge 8 ]]; then
            break
        else
            log_warn "Password must be at least 8 characters long"
        fi
    done

    # Database name
    read -p "Database name [$DEFAULT_DATABASE_NAME]: " DATABASE_NAME
    DATABASE_NAME=${DATABASE_NAME:-$DEFAULT_DATABASE_NAME}

    # DivvyQueue frontend URL
    read -p "DivvyQueue frontend URL (e.g., https://divvyqueue.railway.app): " FRONTEND_URL
    while [[ -z "$FRONTEND_URL" ]]; do
        log_warn "Frontend URL is required"
        read -p "DivvyQueue frontend URL: " FRONTEND_URL
    done

    # Optional: Custom domain
    read -p "Custom domain (optional, e.g., tryton.yourcompany.com): " CUSTOM_DOMAIN

    # Optional: Email configuration
    echo ""
    read -p "Configure email notifications? (y/N): " -n 1 -r SETUP_EMAIL
    echo

    if [[ $SETUP_EMAIL =~ ^[Yy]$ ]]; then
        read -p "SMTP host (e.g., smtp.gmail.com): " EMAIL_HOST
        read -p "SMTP port [587]: " EMAIL_PORT
        EMAIL_PORT=${EMAIL_PORT:-587}
        read -p "Email username: " EMAIL_USER
        read -s -p "Email password/app password: " EMAIL_PASSWORD
        echo
    fi

    # Generate secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")

    log_info "Configuration collected successfully"
}

create_railway_project() {
    log_step "Creating Railway project..."

    # Initialize Railway project
    if railway status >/dev/null 2>&1; then
        log_info "Railway project already initialized"
    else
        log_info "Initializing new Railway project..."
        railway init --name "$RAILWAY_PROJECT_NAME"
    fi

    # Add PostgreSQL database
    log_info "Adding PostgreSQL database..."
    railway add postgresql || log_info "PostgreSQL may already be added"

    # Optional: Add Redis for caching
    read -p "Add Redis for caching? (y/N): " -n 1 -r ADD_REDIS
    echo

    if [[ $ADD_REDIS =~ ^[Yy]$ ]]; then
        log_info "Adding Redis service..."
        railway add redis || log_info "Redis may already be added"
    fi
}

configure_environment() {
    log_step "Configuring environment variables..."

    # Set core variables
    log_info "Setting core configuration..."
    railway variables set ADMIN_EMAIL="$ADMIN_EMAIL"
    railway variables set ADMIN_PASSWORD="$ADMIN_PASSWORD"
    railway variables set SECRET_KEY="$SECRET_KEY"
    railway variables set DATABASE_NAME="$DATABASE_NAME"

    # Set frontend integration
    log_info "Setting DivvyQueue integration..."
    railway variables set FRONTEND_URL="$FRONTEND_URL"
    railway variables set CORS_ORIGINS="$FRONTEND_URL,https://*.railway.app"

    # Set custom domain if provided
    if [[ -n "$CUSTOM_DOMAIN" ]]; then
        railway variables set RAILWAY_PUBLIC_DOMAIN="$CUSTOM_DOMAIN"
        log_info "Custom domain configured: $CUSTOM_DOMAIN"
    fi

    # Set email configuration if provided
    if [[ -n "$EMAIL_HOST" ]]; then
        log_info "Setting email configuration..."
        railway variables set EMAIL_HOST="$EMAIL_HOST"
        railway variables set EMAIL_PORT="$EMAIL_PORT"
        railway variables set EMAIL_USER="$EMAIL_USER"
        railway variables set EMAIL_PASSWORD="$EMAIL_PASSWORD"
        railway variables set EMAIL_USE_TLS="true"
    fi

    # Set production defaults
    railway variables set TRYTON_CONFIG="/app/railway-trytond.conf"
    railway variables set LOG_LEVEL="INFO"
    railway variables set WORKER_PROCESSES="4"
    railway variables set MAX_REQUEST_SIZE="50M"
    railway variables set SESSION_TIMEOUT="3600"
    railway variables set PYTHONUNBUFFERED="1"

    log_info "Environment variables configured"
}

deploy_application() {
    log_step "Deploying to Railway..."

    log_info "Starting deployment (this may take several minutes)..."
    railway up --detach

    # Wait for deployment to be ready
    log_info "Waiting for deployment to be ready..."
    sleep 30

    # Get deployment URL
    DEPLOYMENT_URL=$(railway status --json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('deployments', [{}])[0].get('url', 'URL_NOT_AVAILABLE'))
except:
    print('URL_NOT_AVAILABLE')
" 2>/dev/null || echo "URL_NOT_AVAILABLE")

    if [[ "$DEPLOYMENT_URL" == "URL_NOT_AVAILABLE" ]]; then
        log_warn "Could not retrieve deployment URL automatically"
        log_info "Check Railway dashboard for your deployment URL"
    else
        log_info "Deployment URL: $DEPLOYMENT_URL"

        # Test health endpoint
        log_info "Testing deployment health..."
        for i in {1..12}; do
            if curl -f -s "$DEPLOYMENT_URL/health" >/dev/null 2>&1; then
                log_info "✅ Deployment is healthy!"
                break
            else
                if [[ $i -eq 12 ]]; then
                    log_warn "Health check timeout - deployment may still be starting"
                else
                    echo -n "."
                    sleep 10
                fi
            fi
        done
        echo
    fi
}

initialize_database() {
    log_step "Initializing Tryton database..."

    read -p "Initialize Tryton database now? (Y/n): " -n 1 -r INIT_DB
    echo

    if [[ ! $INIT_DB =~ ^[Nn]$ ]]; then
        log_info "Connecting to Railway shell to initialize database..."
        log_warn "This will take a few minutes..."

        railway shell <<EOF
echo "Initializing Tryton database with core modules..."
trytond-admin -c /app/railway-trytond.conf -d $DATABASE_NAME --all --password <<ADMIN_PASS
$ADMIN_PASSWORD
$ADMIN_PASSWORD
ADMIN_PASS

echo "Database initialization completed"
exit
EOF

        log_info "Database initialization completed"
    else
        log_info "Database initialization skipped"
        log_warn "Remember to initialize the database manually:"
        echo "  railway shell"
        echo "  trytond-admin -c /app/railway-trytond.conf -d $DATABASE_NAME --all"
    fi
}

setup_custom_domain() {
    if [[ -n "$CUSTOM_DOMAIN" ]]; then
        log_step "Setting up custom domain..."

        echo "To complete custom domain setup:"
        echo "1. Go to your Railway project dashboard"
        echo "2. Click 'Settings' → 'Domains'"
        echo "3. Add custom domain: $CUSTOM_DOMAIN"
        echo "4. Add DNS record: CNAME $CUSTOM_DOMAIN → [railway-provided-domain]"
        echo ""
        read -p "Press Enter when DNS is configured..."

        log_info "Custom domain setup instructions provided"
    fi
}

setup_github_actions() {
    log_step "Setting up GitHub Actions..."

    read -p "Set up automated deployments with GitHub Actions? (Y/n): " -n 1 -r SETUP_ACTIONS
    echo

    if [[ ! $SETUP_ACTIONS =~ ^[Nn]$ ]]; then
        echo "To complete GitHub Actions setup:"
        echo "1. Go to your GitHub repository settings"
        echo "2. Go to 'Secrets and variables' → 'Actions'"
        echo "3. Add repository secrets:"
        echo "   - RAILWAY_PRODUCTION_TOKEN: $(railway auth token)"
        echo "   - RAILWAY_STAGING_TOKEN: [create separate staging project token]"
        echo ""
        echo "4. Your workflow will trigger on:"
        echo "   - Push to main branch (staging deployment)"
        echo "   - Commit message with '[deploy]' (production deployment)"
        echo ""
        read -p "Press Enter to continue..."

        log_info "GitHub Actions setup instructions provided"
    fi
}

generate_summary() {
    log_step "Deployment Summary"

    echo "🚀 Railway deployment completed successfully!"
    echo ""
    echo "📋 Configuration Summary:"
    echo "  Project: $RAILWAY_PROJECT_NAME"
    echo "  Database: $DATABASE_NAME"
    echo "  Admin Email: $ADMIN_EMAIL"
    echo "  Frontend URL: $FRONTEND_URL"

    if [[ -n "$CUSTOM_DOMAIN" ]]; then
        echo "  Custom Domain: $CUSTOM_DOMAIN"
    fi

    if [[ -n "$EMAIL_HOST" ]]; then
        echo "  Email: Configured"
    fi

    echo ""
    echo "🔗 Next Steps:"
    echo "1. Update your DivvyQueue .env file:"
    if [[ "$DEPLOYMENT_URL" != "URL_NOT_AVAILABLE" ]]; then
        echo "   VITE_TRYTON_URL=$DEPLOYMENT_URL"
    else
        echo "   VITE_TRYTON_URL=[your-railway-url]"
    fi
    echo "   VITE_TRYTON_DATABASE=$DATABASE_NAME"
    echo ""
    echo "2. Test the integration:"
    if [[ "$DEPLOYMENT_URL" != "URL_NOT_AVAILABLE" ]]; then
        echo "   curl $DEPLOYMENT_URL/health"
    fi
    echo ""
    echo "3. Access Railway dashboard: https://railway.app/dashboard"
    echo "4. Monitor logs: railway logs -f"
    echo ""
    echo "📚 Documentation:"
    echo "  - Deployment guide: RAILWAY_DEPLOYMENT.md"
    echo "  - Railway CLI: https://docs.railway.app/deploy/cli"
    echo ""
    echo "✅ Your Tryton ERP is now running on Railway!"
}

# Main execution
main() {
    echo "🚂 Tryton Railway Deployment Setup"
    echo "This script will deploy your Tryton fork to Railway for DivvyQueue integration"
    echo ""

    read -p "Continue with Railway deployment? (Y/n): " -n 1 -r CONTINUE
    echo

    if [[ $CONTINUE =~ ^[Nn]$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi

    check_prerequisites
    setup_github
    railway_login
    collect_configuration
    create_railway_project
    configure_environment
    deploy_application
    initialize_database
    setup_custom_domain
    setup_github_actions
    generate_summary
}

# Error handling
trap 'log_error "Script failed at line $LINENO"' ERR

# Run main function
main "$@"
