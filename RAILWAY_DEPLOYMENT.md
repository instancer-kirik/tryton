# Railway Deployment Guide for Tryton Fork

This guide will walk you through deploying your Tryton fork to Railway for production use with DivvyQueue.

## Prerequisites

- Railway account (https://railway.app)
- GitHub account with your Tryton fork
- PostgreSQL database (Railway provides this)
- Domain name (optional, but recommended)

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
# Core configuration
railway variables set ADMIN_EMAIL="admin@yourcompany.com"
railway variables set ADMIN_PASSWORD="your-secure-admin-password"
railway variables set SECRET_KEY="your-super-secret-key-here"

# DivvyQueue integration
railway variables set FRONTEND_URL="https://your-divvyqueue-app.railway.app"
railway variables set CORS_ORIGINS="https://your-divvyqueue-app.railway.app,https://*.railway.app"

# Database (auto-set by Railway when you add PostgreSQL)
# DATABASE_URL is automatically configured

# Optional but recommended
railway variables set EMAIL_HOST="smtp.gmail.com"
railway variables set EMAIL_USER="your-email@gmail.com" 
railway variables set EMAIL_PASSWORD="your-app-password"
```

### 5. Deploy

```bash
# Deploy via CLI
railway up

# Or push to trigger GitHub Actions
git push origin main
```

## Detailed Configuration

### Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | Auto-set by Railway |
| `ADMIN_EMAIL` | Yes | Administrator email | `admin@company.com` |
| `ADMIN_PASSWORD` | Yes | Administrator password | `SecurePass123!` |
| `SECRET_KEY` | Yes | Django secret key | `your-secret-key` |
| `FRONTEND_URL` | Yes | DivvyQueue frontend URL | `https://app.railway.app` |
| `CORS_ORIGINS` | Yes | Allowed CORS origins | `https://app.com,*.railway.app` |
| `DATABASE_NAME` | No | Database name | `divvyqueue_prod` |
| `LOG_LEVEL` | No | Logging level | `INFO` |
| `WORKER_PROCESSES` | No | Gunicorn workers | `4` |
| `SESSION_TIMEOUT` | No | Session timeout in seconds | `3600` |
| `MAX_REQUEST_SIZE` | No | Max request size | `50M` |
| `EMAIL_HOST` | No | SMTP host | `smtp.gmail.com` |
| `EMAIL_PORT` | No | SMTP port | `587` |
| `EMAIL_USER` | No | SMTP username | `user@gmail.com` |
| `EMAIL_PASSWORD` | No | SMTP password | `app-password` |
| `REDIS_URL` | No | Redis cache URL | Auto-set if Redis added |

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

# Initialize Tryton database with all modules
trytond-admin -c /app/railway-trytond.conf -d divvyqueue_prod --all

# Set admin password
trytond-admin -c /app/railway-trytond.conf -d divvyqueue_prod --password
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

For debugging, temporarily enable debug mode:

```bash
railway variables set LOG_LEVEL="DEBUG"
railway variables set DEBUG_ENABLED="true"

# Remember to disable in production
railway variables set LOG_LEVEL="INFO"
railway variables set DEBUG_ENABLED="false"
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

1. **Check logs first**: `railway logs -f`
2. **Review configuration**: `railway variables list`
3. **Test locally**: Use the same configuration locally
4. **Railway Support**: Use Railway Discord or support
5. **Tryton Issues**: Check Tryton documentation and forums

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

This completes your Railway deployment setup for the Tryton fork! Your ERP system will be accessible via Railway's URL and ready for DivvyQueue integration.