# Railway Deployment Guide for Tryton Fork

This guide will walk you through deploying your Tryton fork to Railway for production use with DivvyQueue, with a focus on security best practices.

## Prerequisites

- Railway account (https://railway.app)
- GitHub account with your Tryton fork
- PostgreSQL database (Railway provides this)
- Domain name (optional, but recommended)
- Strong, unique passwords for all accounts
- Understanding of basic security principles

## 🔒 Security First Approach

**IMPORTANT**: This deployment includes security improvements to prevent common vulnerabilities. Please review `SECURITY.md` for detailed security requirements.

## Quick Start

### 1. Prepare Your Repository

```bash
# Navigate to your Tryton fork
cd /home/kirik/Code/others/tryton

# Ensure all Railway files are committed
git add railway.toml Dockerfile requirements.txt railway-trytond.conf
git add .github/workflows/railway-deploy.yml
git commit -m "Add Railway deployment configuration"
git push origin main
```

### 2. Create Railway Project

#### Option A: Railway Dashboard
1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your Tryton fork repository
5. Railway will auto-detect the configuration

#### Option B: Railway CLI
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Clone your repository if not local
git clone https://github.com/YOUR_USERNAME/tryton.git
cd tryton

# Initialize Railway project
railway init

# Link to existing project (if you created one in dashboard)
railway link
```

### 3. Add PostgreSQL Database

```bash
# Via CLI
railway add postgresql

# Or in Railway Dashboard:
# 1. Go to your project
# 2. Click "New" → "Database" → "PostgreSQL"
```

### 4. Set Environment Variables

#### Required Variables
Set these in Railway Dashboard or via CLI:

```bash
# SECURITY CRITICAL: Use strong, unique values for all variables
# Core configuration
railway variables set ADMIN_EMAIL="admin@yourcompany.com"
railway variables set ADMIN_PASSWORD="YourVerySecurePassword123!"  # 12+ chars, mixed case, numbers, symbols
railway variables set SECRET_KEY="$(openssl rand -base64 32)"      # Generate cryptographically secure key

# Session security
railway variables set SESSION_SECRET="$(openssl rand -base64 32)"  # Unique session encryption key
railway variables set SESSION_TIMEOUT="3600"                       # 1 hour session timeout

# DivvyQueue integration
railway variables set FRONTEND_URL="https://your-divvyqueue-app.railway.app"
railway variables set CORS_ORIGINS="https://your-divvyqueue-app.railway.app"  # NO wildcards!

# Database (auto-set by Railway when you add PostgreSQL)
# DATABASE_URL is automatically configured with SSL

# Optional but recommended for production
railway variables set LOG_LEVEL="INFO"                             # Never DEBUG in production
railway variables set EMAIL_HOST="smtp.gmail.com"
railway variables set EMAIL_USER="your-email@gmail.com"
railway variables set EMAIL_PASSWORD="your-app-password"           # Use app-specific password
```

#### ⚠️ Security Validation
Before deployment, run the validation script:

```bash
# Validate your environment variables for security
python3 validate_env.py
```

### 5. Deploy

```bash
# Deploy via CLI
railway up

# Or push to trigger GitHub Actions
git push origin main
```

## Detailed Configuration

### 🛡️ Security Configuration

Before configuring variables, review these security requirements:

1. **Never use default or weak passwords**
2. **Generate cryptographically secure secrets**
3. **Use HTTPS-only URLs**
4. **Restrict CORS to specific domains**
5. **Keep sensitive data out of logs**

### Environment Variables Reference

| Variable | Required | Security Level | Description | Example |
|----------|----------|-------------|-------------|---------|
| `DATABASE_URL` | Yes | 🔴 Critical | PostgreSQL connection with SSL | Auto-set by Railway |
| `ADMIN_PASSWORD` | Yes | 🔴 Critical | Strong admin password (12+ chars) | `MySecure123!Pass` |
| `SECRET_KEY` | Yes | 🔴 Critical | Cryptographic key (32+ chars) | `$(openssl rand -base64 32)` |
| `FRONTEND_URL` | Yes | 🟡 Important | DivvyQueue frontend URL (HTTPS only) | `https://app.railway.app` |
| `CORS_ORIGINS` | Yes | 🟡 Important | Specific allowed origins (no wildcards) | `https://app.com` |
| `SESSION_SECRET` | Recommended | 🟡 Important | Session encryption key | `$(openssl rand -base64 32)` |
| `ADMIN_EMAIL` | Recommended | 🟢 Standard | Administrator email | `admin@company.com` |
| `DATABASE_NAME` | No | 🟢 Standard | Database name | `divvyqueue_prod` |
| `LOG_LEVEL` | No | 🟡 Important | Logging level (INFO for prod) | `INFO` |
| `SESSION_TIMEOUT` | No | 🟡 Important | Session timeout in seconds | `3600` |
| `EMAIL_HOST` | No | 🟢 Standard | SMTP host | `smtp.gmail.com` |
| `EMAIL_PORT` | No | 🟢 Standard | SMTP port | `587` |
| `EMAIL_USER` | No | 🟢 Standard | SMTP username | `user@gmail.com` |
| `EMAIL_PASSWORD` | No | 🟡 Important | SMTP app-specific password | `app-password` |
| `REDIS_URL` | No | 🟢 Standard | Redis cache URL | Auto-set if Redis added |

#### ❌ Forbidden Values in Production
- `ADMIN_PASSWORD`: `admin`, `password`, `123456`, `root`, `tryton`
- `SECRET_KEY`: `dev`, `development`, `secret`, `changeme`
- `LOG_LEVEL`: `DEBUG`
- `CORS_ORIGINS`: `*`, `http://localhost`

### Custom Domain Setup

1. **In Railway Dashboard:**
   - Go to your project
   - Click "Settings" → "Domains"
   - Click "Custom Domain"
   - Enter your domain (e.g., `tryton.yourcompany.com`)

2. **DNS Configuration:**
   - Add CNAME record: `tryton.yourcompany.com` → `your-project.railway.app`
   - Wait for propagation (5-30 minutes)

3. **Update Environment Variables:**
   ```bash
   railway variables set FRONTEND_URL="https://app.yourcompany.com"
   railway variables set CORS_ORIGINS="https://app.yourcompany.com,https://yourcompany.com"
   ```

### SSL Certificate

Railway automatically provides SSL certificates for custom domains. No additional configuration needed.

## Database Management

### Initial Database Setup

After first deployment, initialize the database:

```bash
# Connect to Railway shell
railway shell

# The database is automatically initialized on first deployment
# If manual initialization is needed:
trytond-admin -c /app/railway-trytond.conf -d divvyqueue_prod --all

# Admin password is set via ADMIN_PASSWORD environment variable
# No manual password setting needed
```

### Database Backups

#### Manual Backup
```bash
# Connect to your project
railway shell

# Create backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Download backup (if needed)
# Railway doesn't have direct file download, so use external storage
```

#### Automated Backups
Railway PostgreSQL includes automatic backups. Access them in:
1. Railway Dashboard
2. Go to your PostgreSQL service
3. Click "Backups" tab

### Database Migrations

When you update Tryton modules:

```bash
railway shell
trytond-admin -c /app/railway-trytond.conf -d divvyqueue_prod -u module_name
```

## Monitoring and Logging

### View Logs

```bash
# Via CLI - follow logs in real-time
railway logs -f

# View specific service logs
railway logs -f --service tryton

# View recent logs
railway logs --tail 100
```

### Health Checks

Your deployment includes a health endpoint:
- URL: `https://your-app.railway.app/health`
- Returns JSON status of database and application

### Performance Monitoring

Railway provides built-in metrics:
1. Go to your project dashboard
2. Check "Metrics" tab for CPU, Memory, Network usage

## Scaling and Performance

### Vertical Scaling

Railway auto-scales based on usage, but you can configure:

```bash
# Set resource limits (in railway.toml)
[deploy]
replicas = 2
healthcheckPath = "/health"
healthcheckTimeout = 60
```

### Database Performance

1. **Connection Pooling**: Configured in `railway-trytond.conf`
2. **Query Optimization**: Monitor slow queries in logs
3. **Indexing**: Add database indexes for frequently queried fields

### Caching

Add Redis for better performance:

```bash
# Add Redis service
railway add redis

# Redis URL will be auto-set in REDIS_URL variable
```

## Security Considerations

### Environment Variables
- Never commit secrets to Git
- Use Railway's secret management
- Rotate passwords regularly

### Network Security
- CORS is configured for your specific domain
- HTTPS is enforced automatically
- Database is only accessible from your app

### Access Control
- Use strong admin passwords
- Implement proper user roles in Tryton
- Regular security updates

## Troubleshooting

### Common Issues

#### Deployment Fails
```bash
# Check build logs
railway logs --deployment latest

# Check configuration
railway variables list

# Verify requirements.txt is valid
pip install -r requirements.txt --dry-run
```

#### Database Connection Error
```bash
# Check DATABASE_URL is set
railway variables get DATABASE_URL

# Test connection
railway shell
python -c "import psycopg2; psycopg2.connect('$DATABASE_URL'); print('OK')"
```

#### Application Won't Start
```bash
# Check application logs
railway logs -f

# Test configuration locally
python -c "from trytond.config import config; config.update_etc('railway-trytond.conf')"
```

#### Health Check Fails
```bash
# Test health endpoint
curl https://your-app.railway.app/health

# Check if database is initialized
railway shell
python -c "from trytond.pool import Pool; Pool('divvyqueue_prod')"
```

### Debug Mode

⚠️ **SECURITY WARNING**: Never enable debug mode in production!

For staging environment debugging only:

```bash
# Only for staging environment
railway variables set --environment staging LOG_LEVEL="DEBUG"

# Production should always use:
railway variables set --environment production LOG_LEVEL="INFO"
```

## DivvyQueue Integration

### Update DivvyQueue Configuration

After successful deployment, update your DivvyQueue `.env`:

```env
VITE_TRYTON_URL=https://your-tryton-app.railway.app
VITE_TRYTON_DATABASE=divvyqueue_prod
VITE_TRYTON_TIMEOUT=30000
```

### Test Integration

```bash
# Test health endpoint first
curl https://your-tryton-app.railway.app/health

# Test Tryton API from DivvyQueue
curl -X POST https://your-tryton-app.railway.app/divvyqueue_prod/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"common.version","params":[],"id":1}'
```

## Continuous Deployment

### GitHub Actions

The included workflow (`.github/workflows/railway-deploy.yml`) provides:

- **Automatic staging deployment** on every push to `main`
- **Production deployment** when commit message contains `[deploy]`
- **Manual deployment** via GitHub Actions UI

### Deploy to Production

```bash
# Method 1: Commit message trigger
git commit -m "Update user interface [deploy]"
git push origin main

# Method 2: GitHub Actions UI
# Go to Actions tab → "Deploy Tryton to Railway" → Run workflow

# Method 3: Railway CLI
railway up --environment production
```

### Rollback

```bash
# View deployments
railway deployments list

# Rollback to previous deployment
railway rollback

# Rollback to specific deployment
railway rollback <deployment-id>
```

## 🔒 Security Resources

### Security Documentation
- **SECURITY.md** - Complete security checklist and best practices
- **validate_env.py** - Environment variable security validation script
- [Railway Security Docs](https://docs.railway.app/reference/security)

### Quick Security Commands

```bash
# Validate environment security before deployment
python3 validate_env.py

# Generate secure secrets
openssl rand -base64 32  # For SECRET_KEY and SESSION_SECRET

# Check deployment security
curl https://your-app.railway.app/health

# Review security logs
railway logs --tail 100 | grep -i "error\|warning\|security"
```

## Support and Resources

### Railway Resources
- [Railway Documentation](https://docs.railway.app)
- [Railway Discord Community](https://discord.gg/railway)
- [Railway Status Page](https://status.railway.app)

### Tryton Resources
- [Tryton Documentation](https://docs.tryton.org)
- [Tryton Forum](https://discuss.tryton.org)
- [Your Fork Issues](https://github.com/YOUR_USERNAME/tryton/issues)

### Getting Help

1. **Security validation**: `python3 validate_env.py`
2. **Check logs first**: `railway logs -f`
3. **Health check**: `curl https://your-app.railway.app/health`
4. **Review configuration**: `railway variables list` (sensitive values hidden)
5. **Test locally**: Use the same configuration locally
6. **Railway Support**: Use Railway Discord or support
7. **Security issues**: Review SECURITY.md and follow incident response procedures

## Maintenance

### Regular Tasks

#### Weekly
- Review application logs for errors
- Check database size and performance
- Monitor resource usage

#### Monthly
- Update dependencies (create PR)
- Review and rotate secrets
- Check for Tryton updates

#### Quarterly
- Full database backup and test restore
- Security audit
- Performance optimization review

### Updates and Patches

```bash
# Update dependencies
pip list --outdated
# Update requirements.txt accordingly

# Deploy updates
git add requirements.txt
git commit -m "Update dependencies [deploy]"
git push origin main
```

## Cost Optimization

### Railway Pricing

- **Hobby Plan**: $5/month per service
- **Pro Plan**: Pay-as-you-go based on usage
- **Database**: Separate pricing for PostgreSQL

### Optimization Tips

1. **Right-size resources**: Monitor usage and adjust
2. **Database optimization**: Regular VACUUM and indexing
3. **Caching**: Use Redis for frequently accessed data
4. **Image optimization**: Keep Docker image size minimal
5. **Monitoring**: Set up alerts for unusual resource usage

## Advanced Configuration

### Multiple Environments

```bash
# Create staging environment
railway environment create staging

# Deploy to staging
railway up --environment staging

# Set different variables per environment
railway variables set --environment staging LOG_LEVEL=DEBUG
railway variables set --environment production LOG_LEVEL=INFO
```

### Custom Build Process

Modify `railway.toml` for custom build steps:

```toml
[build]
builder = "nixpacks"
buildCommand = """
    echo "Custom build step" && \
    pip install custom-package && \
    python custom-setup.py
"""
```

### Load Balancing

For high-traffic scenarios:

```toml
[deploy]
replicas = 3
startCommand = "gunicorn -w 8 -b 0.0.0.0:$PORT wsgi:application"
```

## 🚀 Final Security Checklist

Before going live, ensure you've completed these security steps:

- [ ] Run `python3 validate_env.py` and fix all errors
- [ ] Review `SECURITY.md` security checklist  
- [ ] Set strong, unique passwords for all accounts
- [ ] Configure CORS for specific domains only
- [ ] Test health endpoint: `/health`
- [ ] Verify HTTPS is working properly
- [ ] Set up monitoring and log alerts
- [ ] Document incident response procedures

## 🎉 Deployment Complete

Your secure Tryton ERP system is now deployed on Railway with production-grade security measures! The system includes:

✅ **Secure configuration management**
✅ **Environment variable validation**  
✅ **Protected sensitive data**
✅ **HTTPS enforcement**
✅ **Restricted CORS policies**
✅ **Security monitoring**

Your ERP system is accessible via Railway's URL and ready for secure DivvyQueue integration.
