# Railway Administration Guide for Tryton Security

This guide shows you how to run security validation and administrative tasks on your Railway-deployed Tryton instance.

## 🚀 Railway Execution Methods

### Method 1: Railway Shell (Interactive)

Railway provides a shell feature that connects directly to your running container:

```bash
# Connect to your Railway service
railway shell

# Once connected, you can run any of these commands:
python3 validate_env.py                    # Environment security validation
python3 railway_admin.py full              # Complete diagnostic suite
python3 railway_admin.py security          # Security-only validation
python3 railway_admin.py health            # Health check
bash pre_deploy_check.sh                   # Pre-deployment validation (if available)
```

### Method 2: HTTP Endpoints (Remote)

Access security information via HTTP endpoints from anywhere:

```bash
# Basic health check with security score
curl https://your-app.railway.app/health

# Detailed health check with security details
curl "https://your-app.railway.app/health?security=detailed"

# Comprehensive security validation
curl https://your-app.railway.app/security-check

# Database diagnostics
curl https://your-app.railway.app/db-diagnostics
```

### Method 3: Automatic Validation (Built-in)

Security validation runs automatically during startup in production:

- ✅ **Production environment**: Full security validation runs before server starts
- ✅ **Automatic failure**: Server won't start if critical security issues found
- ✅ **Startup logs**: Security validation results logged during deployment

## 🔧 Railway Admin Tool Usage

The `railway_admin.py` script provides comprehensive administrative functions:

### Available Commands

```bash
# Full diagnostic suite (recommended)
python3 railway_admin.py full

# Individual checks
python3 railway_admin.py health        # Health and availability
python3 railway_admin.py security      # Security validation  
python3 railway_admin.py database      # Database diagnostics
python3 railway_admin.py config        # Configuration validation
python3 railway_admin.py maintenance   # Maintenance tasks

# Verbose output
python3 railway_admin.py full -v

# Override URL (for testing)
python3 railway_admin.py health --url https://staging-app.railway.app
```

### Example Output

```
🚀 Starting Full Diagnostic Suite
Environment: production  
Application URL: https://your-app.railway.app

🏥 Starting Health Check
✅ Health Status: healthy
✅ Security Score: 95.8/100
✅ Tryton application loaded successfully

🔒 Starting Security Validation  
✅ Environment validation passed
✅ Security validation passed

🗄️ Starting Database Diagnostics
✅ Database connection: OK
📋 Database: divvyqueue_prod
📋 Version: PostgreSQL 15.4
✅ Query performance: 0.045s

⚙️ Checking Configuration
✅ Configuration file exists
✅ Configuration file permissions: secure (600)
✅ Environment variable DATABASE_URL: set
✅ Environment variable ADMIN_PASSWORD: set
✅ Environment variable SECRET_KEY: set

🔧 Running Maintenance Tasks
✅ Cleaned old log files from /tmp
✅ Disk space check completed
✅ Memory check completed

📊 Diagnostic Summary
health_check: PASS
security_validation: PASS  
database_diagnostics: PASS
configuration_check: PASS
maintenance_tasks: PASS
✅ Overall Status: HEALTHY (5/5)
```

## 🛡️ Security Validation Details

### Environment Variable Validation

The security validation checks these critical areas:

**Password Security:**
- ✅ ADMIN_PASSWORD length (≥12 characters)
- ✅ Password complexity (uppercase, lowercase, numbers, symbols)
- ✅ No common weak patterns (admin, password, 123456, etc.)

**Cryptographic Security:**
- ✅ SECRET_KEY length (≥32 characters)
- ✅ SESSION_SECRET presence and uniqueness
- ✅ Database SSL enforcement

**Access Control:**
- ✅ CORS_ORIGINS no wildcards (*)
- ✅ HTTPS-only origins
- ✅ Configuration file permissions (600)

**Production Readiness:**
- ✅ LOG_LEVEL not DEBUG
- ✅ Session timeout reasonable (300-7200 seconds)
- ✅ All required environment variables set

### Health Check Security Score

The `/health` endpoint includes a security score (0-100) based on:

- **Configuration file security** (20 points)
- **Environment variables set** (20 points)
- **Strong admin password** (20 points)
- **Secure CORS policy** (20 points)
- **Database connectivity** (20 points)

Scores 80+ are considered secure for production.

## 🚨 Common Security Issues & Fixes

### Issue: Security Score Below 80

**Symptoms:**
```json
{
  "security": {
    "score": 65.0,
    "status": "needs_attention"
  }
}
```

**Solutions:**
```bash
# Check detailed security status
curl "https://your-app.railway.app/health?security=detailed"

# Run full validation to see specific issues
railway shell
python3 validate_env.py
```

### Issue: CORS Wildcard Error

**Error:** `CORS_ORIGINS contains wildcard (*) - security risk`

**Fix:**
```bash
# Set specific domains only
railway variables set CORS_ORIGINS="https://your-frontend.railway.app,https://yourdomain.com"
```

### Issue: Weak Admin Password

**Error:** `ADMIN_PASSWORD is too short (<12 characters)`

**Fix:**
```bash
# Generate secure password
railway variables set ADMIN_PASSWORD="$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)SecurePass123!"
```

### Issue: Configuration File Permissions

**Error:** `Configuration file permissions: 644 (should be 600)`

**Solution:** This is automatically fixed on next restart. The create_config.py script sets secure permissions.

## 📊 Monitoring & Alerts

### Health Monitoring Script

Create a monitoring script to regularly check your deployment:

```bash
#!/bin/bash
# monitor.sh - Run this from CI/CD or cron job

HEALTH_URL="https://your-app.railway.app/health"
SECURITY_URL="https://your-app.railway.app/security-check"

# Check health
HEALTH_STATUS=$(curl -s $HEALTH_URL | jq -r '.status')
if [ "$HEALTH_STATUS" != "healthy" ]; then
    echo "❌ Health check failed: $HEALTH_STATUS"
    exit 1
fi

# Check security score
SECURITY_SCORE=$(curl -s $HEALTH_URL | jq -r '.security.score')
if (( $(echo "$SECURITY_SCORE < 80" | bc -l) )); then
    echo "⚠️ Security score below 80: $SECURITY_SCORE"
    exit 1
fi

echo "✅ All checks passed - Security score: $SECURITY_SCORE"
```

### Railway Deployment Webhook

Add this to your Railway deployment webhook for automatic validation:

```javascript
// webhook-handler.js
const fetch = require('node-fetch');

async function validateDeployment(deploymentUrl) {
    try {
        // Wait for deployment to be ready
        await new Promise(resolve => setTimeout(resolve, 30000));
        
        // Check health
        const healthResponse = await fetch(`${deploymentUrl}/health`);
        const healthData = await healthResponse.json();
        
        if (healthData.status !== 'healthy') {
            throw new Error(`Deployment unhealthy: ${healthData.status}`);
        }
        
        // Check security
        if (healthData.security && healthData.security.score < 80) {
            console.warn(`Security score below 80: ${healthData.security.score}`);
        }
        
        console.log(`✅ Deployment validated - Security score: ${healthData.security.score}`);
        
    } catch (error) {
        console.error(`❌ Deployment validation failed: ${error.message}`);
        throw error;
    }
}
```

## 🔧 Maintenance Procedures

### Weekly Maintenance

Run these commands weekly via Railway shell:

```bash
railway shell

# Full diagnostic
python3 railway_admin.py full -v

# Check for issues
python3 validate_env.py

# Review logs for security events
# (Railway logs are automatically managed)
```

### Monthly Maintenance

```bash
# Update dependencies (in your development environment)
pip list --outdated
# Update requirements.txt and redeploy

# Security audit
python3 railway_admin.py security -v

# Performance check
python3 railway_admin.py database -v
```

### Quarterly Maintenance

```bash
# Rotate secrets (in Railway dashboard)
railway variables set SECRET_KEY="$(openssl rand -base64 32)"
railway variables set SESSION_SECRET="$(openssl rand -base64 32)"

# Change admin password
railway variables set ADMIN_PASSWORD="NewSecurePassword123!"

# Full security audit
python3 railway_admin.py full -v > security_audit_$(date +%Y%m%d).log
```

## 🚨 Security Incident Response

### Step 1: Immediate Assessment

```bash
# Connect to Railway shell immediately
railway shell

# Run emergency diagnostic  
python3 railway_admin.py full -v

# Check for unauthorized access
curl "https://your-app.railway.app/health?security=detailed"
```

### Step 2: Secure the Environment

```bash
# Rotate all secrets immediately
railway variables set ADMIN_PASSWORD="NewEmergencyPassword$(date +%s)!"
railway variables set SECRET_KEY="$(openssl rand -base64 32)"
railway variables set SESSION_SECRET="$(openssl rand -base64 32)"

# Force restart
railway up --detach
```

### Step 3: Investigation

```bash
# Check Railway logs for suspicious activity
railway logs --tail 1000 | grep -i "error\|fail\|unauthorized\|security"

# Review database diagnostics
python3 railway_admin.py database -v

# Full security validation
python3 validate_env.py
```

## 📞 Support & Resources

### Quick Reference Commands

```bash
# Essential security commands for Railway
railway shell                                    # Connect to container
python3 validate_env.py                         # Validate security
python3 railway_admin.py full                   # Complete diagnostic
curl https://your-app.railway.app/health        # External health check
curl https://your-app.railway.app/security-check # Security validation via HTTP
```

### Getting Help

1. **Security Validation Fails:**
   - Run `python3 validate_env.py` for detailed error messages
   - Check `SECURITY.md` for security requirements
   - Review Railway environment variables

2. **Health Check Fails:**
   - Check Railway deployment logs: `railway logs`
   - Verify database connectivity
   - Check configuration file permissions

3. **Database Issues:**
   - Run `python3 railway_admin.py database -v`
   - Check `DATABASE_URL` environment variable
   - Review Railway PostgreSQL service status

4. **Railway Support:**
   - Railway Discord: https://discord.gg/railway
   - Railway Documentation: https://docs.railway.app
   - Railway Status: https://status.railway.app

### Emergency Contacts

- **Security Issues:** Review `SECURITY.md` incident response procedures
- **Railway Service Issues:** Check Railway status page
- **Application Issues:** Review Railway logs and run diagnostics

---

## 🎯 Best Practices Summary

✅ **Regular Monitoring:** Run `python3 railway_admin.py full` weekly  
✅ **Security Validation:** Always run `python3 validate_env.py` before deployment  
✅ **Environment Secrets:** Rotate secrets quarterly  
✅ **Health Checks:** Monitor `/health` endpoint for security score  
✅ **Incident Response:** Have procedures documented and tested  
✅ **Logging:** Review Railway logs regularly for security events  

Your Tryton deployment includes comprehensive security validation and administrative tools. Use them regularly to maintain a secure, production-ready system! 🚀🔒