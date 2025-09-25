# Tryton ERP - Railway Deployment

Production-ready Tryton ERP deployment for DivvyQueue integration on Railway.

## 🚀 Quick Deploy

```bash
# 1. Clone your Tryton fork
git clone https://github.com/YOUR_USERNAME/tryton.git
cd tryton

# 2. Run the automated setup
./setup-railway.sh

# 3. Update DivvyQueue configuration
# Add to your DivvyQueue .env:
VITE_TRYTON_URL=https://your-app.railway.app
VITE_TRYTON_DATABASE=divvyqueue_prod
```

## 📋 What's Included

- **Production-ready Dockerfile** with multi-stage builds
- **Gunicorn WSGI server** with optimized configuration
- **PostgreSQL database** with automatic backups
- **Redis caching** for improved performance
- **Health checks** and monitoring endpoints
- **GitHub Actions** for automated CI/CD
- **Custom domain support** with SSL
- **Email notifications** (SMTP)
- **Environment-specific configurations**

## 🏗️ Architecture

```
Railway Services:
├── Tryton Web Service (Gunicorn + Python 3.11)
├── PostgreSQL Database
├── Redis Cache (optional)
└── Custom Domain + SSL
```

**Supported Tryton Modules:**
- Party Management
- Product Catalog
- Sales & Purchase
- Accounting & Finance
- Stock Management
- Project Management
- Company & Currency

## 📚 Documentation

| File | Description |
|------|-------------|
| `RAILWAY_DEPLOYMENT.md` | Complete deployment guide |
| `railway.toml` | Railway configuration |
| `railway-trytond.conf` | Tryton server configuration |
| `Dockerfile` | Production container setup |
| `requirements.txt` | Python dependencies |
| `setup-railway.sh` | Automated deployment script |

## 🔧 Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | Auto-configured |
| `ADMIN_EMAIL` | Administrator email | `admin@company.com` |
| `ADMIN_PASSWORD` | Admin password | `SecurePass123!` |
| `SECRET_KEY` | Session secret | Auto-generated |
| `FRONTEND_URL` | DivvyQueue URL | `https://app.railway.app` |
| `CORS_ORIGINS` | Allowed origins | `https://app.com,*.railway.app` |

### Optional Variables

- `CUSTOM_DOMAIN` - Custom domain name
- `EMAIL_HOST` - SMTP server for notifications
- `REDIS_URL` - Cache server (auto-configured)
- `LOG_LEVEL` - Logging verbosity (INFO/DEBUG)
- `WORKER_PROCESSES` - Gunicorn workers (default: 4)

## 🚦 Deployment Options

### Automated Setup (Recommended)
```bash
./setup-railway.sh
```

### Manual Railway CLI
```bash
railway login
railway init
railway add postgresql
railway up
```

### GitHub Actions
Automatic deployments on:
- Push to `main` → Staging
- Commit with `[deploy]` → Production
- Manual trigger via Actions tab

## 🔍 Health Monitoring

| Endpoint | Purpose |
|----------|---------|
| `/health` | Application health status |
| `/metrics` | Performance metrics |
| Railway Dashboard | Resource monitoring |

**Health Check Response:**
```json
{
  "status": "healthy",
  "timestamp": 1640995200,
  "database": "divvyqueue_prod",
  "version": "6.0"
}
```

## 📊 Scaling

### Automatic Scaling
Railway auto-scales based on:
- CPU usage (target: 70%)
- Memory usage (target: 80%)
- Request volume

### Manual Configuration
```toml
# In railway.toml
[deploy]
replicas = 2
healthcheckTimeout = 60
```

### Performance Optimization
- **Database**: Connection pooling, indexing
- **Caching**: Redis for frequent queries
- **Workers**: Multiple Gunicorn processes
- **CDN**: Static file optimization

## 🔐 Security Features

- **HTTPS**: Automatic SSL certificates
- **CORS**: Restricted to your domains
- **Authentication**: Bcrypt password hashing
- **Sessions**: Secure session management
- **Environment Variables**: Secret management
- **Database**: Encrypted connections

## 🛠️ Development Workflow

### Local Development
```bash
# Start local Tryton (from divvyqueue/scripts)
./setup-tryton.sh

# Test Railway config locally
docker build -t tryton-test .
docker run -p 8000:8000 tryton-test
```

### Testing
```bash
# Test deployment health
curl https://your-app.railway.app/health

# Test Tryton API
curl -X POST https://your-app.railway.app/divvyqueue_prod/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"common.version","params":[],"id":1}'
```

### Deployment
```bash
# Staging deployment
git push origin main

# Production deployment  
git commit -m "Deploy to production [deploy]"
git push origin main

# Manual deployment
railway up --environment production
```

## 🐛 Troubleshooting

### Common Issues

**Build Fails**
```bash
railway logs --deployment latest
# Check requirements.txt and Dockerfile
```

**Database Connection Error**
```bash
railway variables get DATABASE_URL
# Verify PostgreSQL service is running
```

**Application Won't Start**
```bash
railway logs -f
# Check tryton configuration and modules
```

**Health Check Fails**
```bash
# Test locally first
python health_check.py
# Check database initialization
```

### Debug Mode
```bash
railway variables set LOG_LEVEL=DEBUG
railway variables set DEBUG_ENABLED=true
```

## 🔄 Maintenance

### Database Management
```bash
# Initialize database
railway shell
trytond-admin -c /app/railway-trytond.conf -d divvyqueue_prod --all

# Backup database
pg_dump $DATABASE_URL > backup.sql

# Update modules
trytond-admin -c /app/railway-trytond.conf -d divvyqueue_prod -u module_name
```

### Updates
```bash
# Update dependencies
pip list --outdated
# Update requirements.txt

# Deploy updates
git commit -m "Update dependencies [deploy]"
git push origin main
```

### Monitoring
- **Logs**: `railway logs -f`
- **Metrics**: Railway Dashboard → Metrics
- **Status**: `curl /health`

## 💰 Cost Optimization

### Railway Pricing
- **Hobby**: $5/month per service
- **Pro**: Usage-based billing
- **Database**: Separate PostgreSQL pricing

### Optimization Tips
1. **Right-size resources** - Monitor CPU/Memory usage
2. **Database tuning** - Regular VACUUM, proper indexing
3. **Caching** - Use Redis for repeated queries
4. **Image size** - Multi-stage Docker builds
5. **Monitoring** - Set usage alerts

## 🤝 Support

### Resources
- 📖 [Full Deployment Guide](RAILWAY_DEPLOYMENT.md)
- 🌐 [Railway Documentation](https://docs.railway.app)
- 💬 [Railway Discord](https://discord.gg/railway)
- 📋 [Tryton Documentation](https://docs.tryton.org)

### Getting Help
1. Check logs: `railway logs -f`
2. Review variables: `railway variables list`
3. Test locally with same config
4. Railway Discord community
5. Tryton forums for ERP issues

## 🎯 Integration with DivvyQueue

### Frontend Configuration
```env
# DivvyQueue .env
VITE_TRYTON_URL=https://your-tryton.railway.app
VITE_TRYTON_DATABASE=divvyqueue_prod
VITE_TRYTON_TIMEOUT=30000
```

### API Testing
```javascript
// Test connection from DivvyQueue
const response = await fetch('https://your-tryton.railway.app/health');
const status = await response.json();
console.log('Tryton Status:', status);
```

### Data Flow
```
DivvyQueue Frontend → Railway Tryton → PostgreSQL
                  ↓
              Supabase (for media/users)
```

## 📈 Production Checklist

- [ ] Environment variables configured
- [ ] Database initialized with modules  
- [ ] Custom domain configured (optional)
- [ ] SSL certificate active
- [ ] Health checks passing
- [ ] GitHub Actions configured
- [ ] Monitoring alerts set up
- [ ] Backup strategy in place
- [ ] DivvyQueue integration tested
- [ ] Performance monitoring enabled

---

**🎉 Your Tryton ERP is now production-ready on Railway!**

Need help? Check the [detailed deployment guide](RAILWAY_DEPLOYMENT.md) or run `./setup-railway.sh` for automated setup.