# 🚀 Storm Oracle Production Deployment Guide

## 🌐 Deployment Options Overview

### 1. **Emergent Platform Deployment (Recommended)**
- ✅ **Easiest**: One-click deployment
- ✅ **Managed**: Auto-scaling, monitoring included
- ✅ **Secure**: Built-in SSL, security features
- ✅ **Cost-effective**: Pay-as-you-scale

### 2. **Cloud Provider Deployment**
- AWS, Google Cloud, Azure
- Full control over infrastructure
- Requires DevOps expertise

### 3. **Self-Hosted Deployment**
- Your own servers/VPS
- Maximum control and customization
- Full responsibility for maintenance

## 🎯 Emergent Platform Deployment (Fastest)

### Step 1: Prepare for Deployment
```bash
# Ensure all services are working locally
sudo supervisorctl status all

# Test the application
curl -s http://localhost:3000 | grep "Storm Oracle"
curl -s https://weather-insight.preview.emergentagent.com/api/radar-stations | jq length
```

### Step 2: Environment Configuration
```bash
# Create production environment file
cp /app/backend/.env /app/backend/.env.production

# Edit production settings
nano /app/backend/.env.production
```

```env
# Production Environment Variables
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/storm_oracle_prod
DB_NAME=storm_oracle_production
JWT_SECRET_KEY=production-super-secret-jwt-key-256-bit
EMERGENT_LLM_KEY=your-emergent-llm-key

# Email Configuration (Production SMTP)
MAIL_USERNAME=noreply@stormoracle.com
MAIL_PASSWORD=production-smtp-password
MAIL_FROM=noreply@stormoracle.com
MAIL_SERVER=smtp.mailgun.org

# Admin Configuration
ADMIN_SECRET_CODE=PRODUCTION_ADMIN_SECRET_2025
ADMIN_EMAILS=admin@stormoracle.com,support@stormoracle.com

# External Services
BACKEND_URL=https://api.stormoracle.com
CORS_ORIGINS=https://stormoracle.com,https://www.stormoracle.com
```

### Step 3: Frontend Production Build
```bash
# Navigate to frontend
cd /app/frontend

# Create production environment
cp .env .env.production
nano .env.production
```

```env
# Production Frontend Environment
REACT_APP_BACKEND_URL=https://api.stormoracle.com
REACT_APP_APP_NAME=Storm Oracle
REACT_APP_VERSION=1.0.0
REACT_APP_ENVIRONMENT=production
```

```bash
# Build production bundle
npm run build

# Test production build locally
npm install -g serve
serve -s build -l 3000
```

### Step 4: Deploy to Emergent Platform
```bash
# Push to GitHub (Emergent will auto-deploy)
git add .
git commit -m "feat: production deployment ready"
git push origin main

# Or use Emergent CLI (if available)
emergent deploy --env production
```

## ☁️ Cloud Provider Deployment

### AWS Deployment with Docker

#### Step 1: Create Dockerfile
```dockerfile
# /app/Dockerfile.backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gfortran \
    libhdf5-dev \
    libnetcdf-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ .

# Expose port
EXPOSE 8001

# Start application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

```dockerfile
# /app/Dockerfile.frontend
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci --only=production

# Copy and build
COPY frontend/ .
RUN npm run build

# Serve with nginx
FROM nginx:alpine
COPY --from=0 /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Step 2: Docker Compose for Production
```yaml
# /app/docker-compose.prod.yml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8001:8001"
    environment:
      - MONGO_URL=mongodb://mongo:27017
      - DB_NAME=storm_oracle_prod
    depends_on:
      - mongo
    restart: unless-stopped
    
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
    restart: unless-stopped
    
  mongo:
    image: mongo:6.0
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=production-password
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

volumes:
  mongo_data:
```

#### Step 3: AWS ECS/Fargate Deployment
```yaml
# /app/aws-task-definition.json
{
  "family": "storm-oracle",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "your-account.dkr.ecr.region.amazonaws.com/storm-oracle-backend:latest",
      "portMappings": [
        {
          "containerPort": 8001,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "MONGO_URL",
          "value": "mongodb+srv://user:pass@cluster.mongodb.net/storm_oracle"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/storm-oracle",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Kubernetes Deployment

#### Step 1: Kubernetes Manifests
```yaml
# /app/k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: storm-oracle
---
# /app/k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: storm-oracle
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: storm-oracle/backend:latest
        ports:
        - containerPort: 8001
        env:
        - name: MONGO_URL
          valueFrom:
            secretKeyRef:
              name: mongo-secret
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: storm-oracle
spec:
  selector:
    app: backend
  ports:
  - port: 8001
    targetPort: 8001
  type: ClusterIP
```

```yaml
# /app/k8s/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: storm-oracle
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: storm-oracle/frontend:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: storm-oracle
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

#### Step 2: Deploy to Kubernetes
```bash
# Deploy to cluster
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n storm-oracle
kubectl get services -n storm-oracle

# Scale if needed
kubectl scale deployment backend --replicas=5 -n storm-oracle
```

## 🌍 Domain and SSL Setup

### 1. Domain Configuration
```bash
# DNS Records to configure:
# A Record: stormoracle.com -> YOUR_SERVER_IP
# A Record: api.stormoracle.com -> YOUR_SERVER_IP
# CNAME: www.stormoracle.com -> stormoracle.com
```

### 2. SSL Certificate (Let's Encrypt)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Generate SSL certificates
sudo certbot --nginx -d stormoracle.com -d www.stormoracle.com -d api.stormoracle.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. Nginx Configuration
```nginx
# /etc/nginx/sites-available/storm-oracle
server {
    listen 80;
    server_name stormoracle.com www.stormoracle.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name stormoracle.com www.stormoracle.com;
    
    ssl_certificate /etc/letsencrypt/live/stormoracle.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stormoracle.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 443 ssl http2;
    server_name api.stormoracle.com;
    
    ssl_certificate /etc/letsencrypt/live/stormoracle.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stormoracle.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📊 Production Monitoring

### 1. Application Monitoring
```python
# /app/backend/monitoring.py
import logging
import time
from prometheus_client import Counter, Histogram, Gauge

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests')
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')
ACTIVE_USERS = Gauge('active_users_total', 'Active users')

@app.middleware("http")
async def monitoring_middleware(request, call_next):
    start_time = time.time()
    REQUEST_COUNT.inc()
    
    response = await call_next(request)
    
    REQUEST_LATENCY.observe(time.time() - start_time)
    return response
```

### 2. Health Checks
```python
# /app/backend/health.py
@api_router.get("/health")
async def health_check():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": await check_database_connection(),
            "redis": await check_redis_connection(),
            "ml_model": await check_ml_model_status(),
            "external_apis": await check_external_apis()
        }
    }
    
    if not all(health_status["checks"].values()):
        health_status["status"] = "unhealthy"
        
    return health_status
```

### 3. Log Management
```yaml
# /app/docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
      
  logstash:
    image: docker.elastic.co/logstash/logstash:8.0.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
      
  kibana:
    image: docker.elastic.co/kibana/kibana:8.0.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

## 🔒 Security Hardening

### 1. Environment Security
```bash
# Secure environment variables
sudo chmod 600 /app/backend/.env
sudo chown app:app /app/backend/.env

# Firewall configuration
sudo ufw enable
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw deny 8001/tcp  # Block direct backend access
```

### 2. Database Security
```javascript
// MongoDB security configuration
db.createUser({
  user: "storm_oracle_app",
  pwd: "secure-random-password",
  roles: [
    { role: "readWrite", db: "storm_oracle_prod" }
  ]
});

// Enable authentication
// In /etc/mongod.conf:
// security:
//   authorization: enabled
```

### 3. API Rate Limiting
```python
# /app/backend/rate_limiting.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@api_router.get("/api/radar-data/{station_id}")
@limiter.limit("100/minute")  # Limit API calls
async def get_radar_data(request: Request, station_id: str):
    # API implementation
```

## 📈 Performance Optimization

### 1. Caching Strategy
```python
# /app/backend/caching.py
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

async def cached_radar_data(station_id: str):
    cache_key = f"radar:{station_id}:{int(time.time() // 300)}"  # 5-minute cache
    
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Generate fresh data
    data = await generate_radar_data(station_id)
    redis_client.setex(cache_key, 300, json.dumps(data))
    return data
```

### 2. CDN Configuration
```javascript
// CloudFlare/AWS CloudFront configuration
const cdnConfig = {
  origins: ['https://api.stormoracle.com'],
  behaviors: {
    '/api/radar-image/*': {
      cacheTTL: 300,  // 5 minutes
      compress: true
    },
    '/static/*': {
      cacheTTL: 86400,  // 24 hours
      compress: true
    }
  }
}
```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# /.github/workflows/deploy.yml
name: Deploy Storm Oracle

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          cd backend && python -m pytest
          cd frontend && npm test
          
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to production
        env:
          DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
        run: |
          # Build and deploy
          docker build -t storm-oracle/backend:latest -f Dockerfile.backend .
          docker build -t storm-oracle/frontend:latest -f Dockerfile.frontend .
          
          # Push to registry
          docker push storm-oracle/backend:latest
          docker push storm-oracle/frontend:latest
          
          # Deploy to production
          kubectl set image deployment/backend backend=storm-oracle/backend:latest
          kubectl set image deployment/frontend frontend=storm-oracle/frontend:latest
```

## 🎯 Go-Live Checklist

### Pre-Launch Testing
- [ ] Load testing completed (1000+ concurrent users)
- [ ] Security penetration testing passed
- [ ] Backup and recovery procedures tested
- [ ] Monitoring and alerting configured
- [ ] SSL certificates installed and tested
- [ ] Domain DNS properly configured
- [ ] Payment integration tested (if applicable)
- [ ] Email delivery tested
- [ ] ML model performance validated

### Launch Day Tasks
- [ ] DNS cutover completed
- [ ] SSL certificates active
- [ ] Monitoring dashboards active
- [ ] Support team notified
- [ ] Social media announcements ready
- [ ] Press release prepared
- [ ] Customer support documentation updated

### Post-Launch Monitoring
- [ ] Performance metrics baseline established
- [ ] Error rate monitoring active
- [ ] User feedback collection setup
- [ ] A/B testing framework deployed
- [ ] Analytics tracking implemented

This deployment guide will get Storm Oracle running in production with enterprise-grade reliability and security!