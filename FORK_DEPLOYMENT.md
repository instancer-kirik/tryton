# Tryton Fork - GitHub & Railway Deployment Guide

## Setting Up Your GitHub Fork

### 1. Fork the Original Repository

If you haven't already forked Tryton:
1. Go to https://github.com/tryton/tryton
2. Click the "Fork" button in the top-right corner
3. Select your GitHub account as the destination

### 2. Update Git Remotes

Switch your local repository to use your fork:

```bash
# Navigate to your Tryton directory
cd /home/kirik/Code/others/tryton

# Check current remotes
git remote -v

# Remove the original remote (if it exists)
git remote remove origin

# Add your fork as origin (replace YOUR_GITHUB_USERNAME)
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/tryton.git

# Add the original Tryton repo as upstream (for syncing updates)
git remote add upstream https://github.com/tryton/tryton.git

# Verify remotes
git remote -v
# Should show:
# origin    https://github.com/YOUR_GITHUB_USERNAME/tryton.git (fetch)
# origin    https://github.com/YOUR_GITHUB_USERNAME/tryton.git (push)
# upstream  https://github.com/tryton/tryton.git (fetch)
# upstream  https://github.com/tryton/tryton.git (push)
```

### 3. Push to Your Fork

```bash
# Push your current branch to your fork
git push -u origin main

# If you have other branches
git push origin --all

# Push tags
git push origin --tags
```

### 4. Keep Your Fork Updated

Periodically sync with the upstream repository:

```bash
# Fetch upstream changes
git fetch upstream

# Checkout your main branch
git checkout main

# Merge upstream changes
git merge upstream/main

# Push updates to your fork
git push origin main
```

## Railway Deployment

### Prerequisites

1. Railway account (https://railway.app)
2. GitHub account with your Tryton fork
3. PostgreSQL database

### Railway Setup

#### 1. Create New Project

```bash
# Install Railway CLI (if not already installed)
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init
```

#### 2. Create `railway.toml` Configuration

Create this file in your Tryton repository root:

```toml
[build]
builder = "NIXPACKS"
buildCommand = """
    pip install -e trytond -e proteus && \
    pip install -r requirements.txt && \
    pip install psycopg2-binary gunicorn
"""

[deploy]
startCommand = "gunicorn -w 4 -b 0.0.0.0:$PORT 'trytond.wsgi:app'"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[environments.production]
TRYTOND_DATABASE_URI = "${{DATABASE_URL}}"
TRYTOND_CONFIG = "/app/trytond-railway.conf"
```

#### 3. Create `trytond-railway.conf`

Create a Railway-specific configuration file:

```ini
[database]
uri = env://TRYTOND_DATABASE_URI

[web]
listen = 0.0.0.0:$PORT
hostname = env://RAILWAY_PUBLIC_DOMAIN
root = /app/sao

[session]
timeout = 3600
super_pwd = env://TRYTON_ADMIN_PASSWORD

[cache]
class = trytond.cache.MemoryCache
clean_timeout = 300
model = 200
record = 2000
field = 100

# Security settings for production
[password]
length = 8
entropy = 0.75

# CORS settings for DivvyQueue frontend
[cors]
origins = env://CORS_ORIGINS

# Email configuration (optional)
[email]
uri = env://EMAIL_URL

[attachment]
store_prefix = /app/attachments

# Logging
[logging]
level = env://LOG_LEVEL
```

#### 4. Create `Dockerfile` (Alternative to Nixpacks)

If you prefer Docker over Nixpacks:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy repository
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e trytond -e proteus && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir psycopg2-binary gunicorn

# Create necessary directories
RUN mkdir -p /app/attachments /app/logs

# Expose port
EXPOSE 8000

# Start command
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "trytond.wsgi:app"]
```

#### 5. Environment Variables for Railway

Set these in Railway dashboard or via CLI:

```bash
railway variables set DATABASE_URL="postgresql://user:pass@host:5432/dbname"
railway variables set TRYTON_ADMIN_PASSWORD="secure_admin_password"
railway variables set CORS_ORIGINS="https://your-divvyqueue-app.railway.app"
railway variables set LOG_LEVEL="INFO"
railway variables set EMAIL_URL="smtp://user:pass@smtp.gmail.com:587?ssl=False&starttls=True"
```

### Deployment Steps

#### 1. Connect GitHub Repository

In Railway Dashboard:
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your Tryton fork repository
4. Railway will auto-deploy on push

#### 2. Add PostgreSQL Database

```bash
# Via Railway CLI
railway add postgresql

# Or in Dashboard:
# 1. Click "New" in your project
# 2. Select "Database"
# 3. Choose "PostgreSQL"
```

#### 3. Initialize Database

After deployment, run initialization:

```bash
# Connect to Railway shell
railway run bash

# Initialize Tryton database
trytond-admin -c trytond-railway.conf -d $DATABASE_NAME --all

# Set admin password
trytond-admin -c trytond-railway.conf -d $DATABASE_NAME --password
```

#### 4. Configure DivvyQueue Connection

Update your DivvyQueue `.env`:

```env
VITE_TRYTON_URL=https://your-tryton-fork.railway.app
VITE_TRYTON_DATABASE=your_database_name
VITE_TRYTON_USE_PROXY=false
```

### GitHub Actions for Auto-Deploy

Create `.github/workflows/railway.yml`:

```yaml
name: Deploy to Railway

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Railway
        run: npm i -g @railway/cli
      
      - name: Deploy to Railway
        run: railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

Add Railway token to GitHub secrets:
1. Get token from Railway: `railway tokens new`
2. Add to GitHub: Settings → Secrets → New repository secret
3. Name: `RAILWAY_TOKEN`

### Monitoring & Logs

#### View Logs

```bash
# Via CLI
railway logs

# Follow logs
railway logs -f

# Or use Railway dashboard for real-time logs
```

#### Health Checks

Add health check endpoint to your Tryton fork:

```python
# In trytond/wsgi.py or custom module
@app.route('/health')
def health_check():
    try:
        # Check database connection
        with Transaction().start(POOL.database_name, 0, readonly=True):
            cursor = Transaction().connection.cursor()
            cursor.execute('SELECT 1')
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503
```

### Production Considerations

#### 1. Security

- Use environment variables for sensitive data
- Enable HTTPS (Railway provides this automatically)
- Set strong admin password
- Configure rate limiting

#### 2. Performance

- Use Redis for caching (add via Railway)
- Configure worker processes based on dyno size
- Enable database connection pooling

#### 3. Backups

```bash
# Manual backup
railway run pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Automated backups - add to railway.toml
[cron]
backup = "0 2 * * * pg_dump $DATABASE_URL > /app/backups/backup_$(date +\\%Y\\%m\\%d).sql"
```

#### 4. Scaling

Railway auto-scales, but you can configure:

```toml
# In railway.toml
[deploy]
replicas = 2
maxReplicas = 10
minReplicas = 1
```

### Troubleshooting

#### Database Connection Issues

```bash
# Test connection
railway run python -c "from trytond.pool import Pool; Pool.start(); print('Connected!')"
```

#### Module Import Errors

```bash
# Verify module installation
railway run python -c "import trytond.modules.your_module"
```

#### Permission Errors

```bash
# Fix permissions
railway run chmod -R 755 /app
railway run chown -R www-data:www-data /app/attachments
```

### Rollback Strategy

```bash
# List deployments
railway deployments list

# Rollback to previous deployment
railway rollback

# Or rollback to specific deployment
railway rollback <deployment-id>
```

## Quick Start Commands

```bash
# 1. Setup your fork
git remote add origin https://github.com/YOUR_USERNAME/tryton.git
git push -u origin main

# 2. Initialize Railway project
railway login
railway init

# 3. Add database
railway add postgresql

# 4. Deploy
railway up

# 5. View logs
railway logs -f
```

## Support Resources

- Railway Documentation: https://docs.railway.app
- Tryton Documentation: https://docs.tryton.org
- Railway Discord: https://discord.gg/railway
- Your fork: https://github.com/YOUR_USERNAME/tryton