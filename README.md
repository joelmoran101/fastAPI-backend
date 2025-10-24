# FastAPI Plotly Backend

A secure, production-ready FastAPI backend for storing and serving Plotly chart data with MongoDB. This backend is part of the **load-json-data** React application ecosystem for rendering Plotly JSON files through different backend APIs.

## 🎯 Project Overview

This FastAPI backend is one of two tested backend implementations for the **load-json-data** React application. It provides a RESTful API for storing, retrieving, updating, and deleting Plotly chart configurations with comprehensive security features.

### Related Projects
- **load-json-data**: Main React frontend application for rendering Plotly charts
- **json-express-api**: Alternative Express.js backend implementation
- **fastAPI-backend** (this project): Python FastAPI implementation

## ✨ Features

### Core Functionality
- ✅ Full CRUD operations for Plotly chart data
- ✅ Structured Plotly JSON format validation
- ✅ MongoDB integration with connection pooling
- ✅ Automatic timestamps and ID generation
- ✅ Pagination support for large datasets

### Security
- 🔒 **CSRF Protection** using synchronizer token pattern
- 🔒 **CORS Configuration** with strict origin control
- 🔒 **Rate Limiting** to prevent abuse (100 req/min)
- 🔒 **Security Headers** (CSP, X-Frame-Options, HSTS)
- 🔒 **Input Validation** with Pydantic models
- 🔒 **NoSQL Injection Prevention**
- 🔒 **Request Size Limits** (10MB max payload)

### Production Ready
- 📊 Comprehensive logging with security event tracking
- 🏥 Health check endpoint with database status
- 🔄 Automatic connection retry and recovery
- 📝 Detailed API documentation (Swagger/ReDoc)
- 🧪 Test-ready with clear structure

## 🏗️ Architecture

```
fastAPI-backend/
├── main.py              # FastAPI application & routes
├── models.py            # Pydantic data models
├── database.py          # MongoDB connection manager
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── .env                 # Local environment config (git-ignored)
├── run.py              # Application runner
├── CSRF_DOCUMENTATION.md  # CSRF implementation guide
└── README.md           # This file
```

## 📋 Prerequisites

- **Python** 3.9+
- **MongoDB** 4.4+ (local) or MongoDB Atlas (cloud)
- **pip** or **poetry** for package management

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd fastAPI-backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=fastapi_plotly_db
COLLECTION_NAME=plotly_data

# CORS Configuration (React app URL)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Security
SECRET_KEY=your-super-secret-key-change-this
RATE_LIMIT_PER_MINUTE=100
```

### 5. Start MongoDB

**Local MongoDB:**
```bash
# macOS (Homebrew)
brew services start mongodb-community

# Linux
sudo systemctl start mongod

# Windows
net start MongoDB
```

**Or use MongoDB Atlas** (cloud) and update `MONGODB_URL` in `.env`

### 6. Run the Application

**Development:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Production:**
```bash
python3 run.py
```

### 7. Verify Installation

Open your browser:
- **API Root**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📡 API Endpoints

### CSRF Protection
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/csrf-token` | Get CSRF token for protected operations |

### Plotly Charts
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/plotly/` | List all charts | - |
| GET | `/plotly/{item_id}` | Get specific chart | - |
| POST | `/plotly/` | Create new chart | CSRF |
| PUT | `/plotly/{item_id}` | Update chart | CSRF |
| DELETE | `/plotly/{item_id}` | Delete chart | CSRF |

### Generic Data (Optional)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/data/` | List all data items | - |
| GET | `/data/{item_id}` | Get specific item | - |
| POST | `/data/` | Create new item | CSRF |
| PUT | `/data/{item_id}` | Update item | CSRF |
| DELETE | `/data/{item_id}` | Delete item | CSRF |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check with DB status |

## 📝 Usage Examples

### Create a Plotly Chart

```bash
# 1. Get CSRF token
curl -c cookies.txt http://localhost:8000/csrf-token

# 2. Extract token
TOKEN=$(grep XSRF-TOKEN cookies.txt | awk '{print $7}')

# 3. Create chart
curl -b cookies.txt \
  -H "X-CSRF-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "title": "Sales Data 2024",
    "description": "Monthly sales chart",
    "chart_type": "line",
    "data": [
      {
        "x": ["Jan", "Feb", "Mar"],
        "y": [100, 150, 200],
        "type": "scatter",
        "mode": "lines+markers",
        "name": "Sales"
      }
    ],
    "layout": {
      "title": "2024 Sales Trend",
      "xaxis": {"title": "Month"},
      "yaxis": {"title": "Revenue"}
    }
  }' \
  http://localhost:8000/plotly/
```

### Retrieve Charts

```bash
# List all charts
curl http://localhost:8000/plotly/

# Get specific chart
curl http://localhost:8000/plotly/1
```

### Python Client Example

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000"
session = requests.Session()

# Get CSRF token
response = session.get(f"{BASE_URL}/csrf-token")
csrf_token = response.cookies.get("XSRF-TOKEN")

# Create chart
chart_data = {
    "title": "Sample Chart",
    "data": [{"x": [1, 2, 3], "y": [4, 5, 6], "type": "scatter"}],
    "layout": {"title": "My Chart"}
}

response = session.post(
    f"{BASE_URL}/plotly/",
    json=chart_data,
    headers={"X-CSRF-Token": csrf_token}
)

print(response.json())
```

## 🔐 Security Implementation

This backend implements enterprise-level security practices:

### CSRF Protection
All state-changing operations (POST, PUT, DELETE) require CSRF tokens using the **double-submit cookie pattern**. See [CSRF_DOCUMENTATION.md](./CSRF_DOCUMENTATION.md) for details.

**Quick Setup:**
```python
# Frontend (axios)
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true
});

// Initialize CSRF on app start
api.get('/csrf-token');

// Interceptor automatically adds token
api.interceptors.request.use((config) => {
  if (!['GET', 'HEAD', 'OPTIONS'].includes(config.method?.toUpperCase())) {
    const token = getCookie('XSRF-TOKEN');
    config.headers['X-CSRF-Token'] = token;
  }
  return config;
});
```

### Rate Limiting
- 100 requests per minute per IP
- Configurable via environment variables
- Automatic cleanup of old request records

### Input Validation
- Pydantic models with strict type checking
- XSS prevention in text fields
- 10MB maximum payload size
- NoSQL injection prevention

## 🧪 Testing

### Manual API Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test CSRF protection (should fail)
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"data": [], "layout": {}}' \
  http://localhost:8000/plotly/
```

### Automated Testing (pytest)

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

**Example Test:**
```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_chart_with_csrf():
    # Get CSRF token
    response = client.get("/csrf-token")
    token = response.cookies.get("XSRF-TOKEN")
    
    # Create chart
    response = client.post(
        "/plotly/",
        json={"data": [{"x": [1,2], "y": [3,4]}], "layout": {}},
        cookies={"XSRF-TOKEN": token},
        headers={"X-CSRF-Token": token}
    )
    
    assert response.status_code == 200
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `DATABASE_NAME` | Database name | `fastapi_plotly_db` |
| `COLLECTION_NAME` | Collection name | `plotly_data` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `http://localhost:3000` |
| `SECRET_KEY` | Application secret key | Required |
| `RATE_LIMIT_PER_MINUTE` | Max requests per minute | `100` |
| `LOG_LEVEL` | Logging level | `INFO` |

### MongoDB Atlas Setup

For cloud MongoDB:

1. Create account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a cluster
3. Get connection string
4. Update `.env`:
```env
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/
DATABASE_NAME=fastapi_plotly_db
```

## 🚢 Deployment

### Production Checklist

- [ ] Change `SECRET_KEY` in `.env`
- [ ] Set `secure=True` for CSRF cookies (requires HTTPS)
- [ ] Update `CORS_ORIGINS` to production domains
- [ ] Configure MongoDB Atlas or production MongoDB
- [ ] Set up Redis for CSRF token storage (distributed systems)
- [ ] Enable HTTPS/TLS
- [ ] Configure rate limiting appropriately
- [ ] Set up monitoring and logging
- [ ] Review and adjust security headers

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t fastapi-plotly-backend .
docker run -p 8000:8000 --env-file .env fastapi-plotly-backend
```

### Using Gunicorn (Production Server)

```bash
pip install gunicorn

gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

## 🔍 Monitoring & Logging

### Application Logs

Logs include:
- Request/response cycles
- Security events (CSRF failures, rate limits)
- Database operations
- Error stack traces

```bash
# View logs in real-time
tail -f app.log
```

### Health Monitoring

```bash
# Automated health check
curl http://localhost:8000/health

# Response format
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-10-24T10:00:00Z"
}
```

## 🛠️ Development

### Code Structure

- **main.py**: Application entry, routes, middleware
- **models.py**: Pydantic schemas and validation
- **database.py**: MongoDB connection management
- **run.py**: Production runner script

### Adding New Endpoints

```python
from fastapi import Depends
from models import PlotlyDataCreate

@app.post("/api/custom", dependencies=[Depends(validate_csrf)])
async def custom_endpoint(data: PlotlyDataCreate):
    # Your logic here
    return {"status": "success"}
```

### Hot Reload During Development

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 🤝 Integration with React Frontend

### Frontend Setup (load-json-data)

```javascript
// src/api/fastapi.js
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_FASTAPI_URL || 'http://localhost:8000',
  withCredentials: true
});

// Initialize CSRF token
export async function initializeCSRF() {
  await api.get('/csrf-token');
}

export default api;
```

### Usage in React Components

```javascript
import { useEffect, useState } from 'react';
import api, { initializeCSRF } from './api/fastapi';

function App() {
  const [charts, setCharts] = useState([]);

  useEffect(() => {
    // Initialize CSRF on mount
    initializeCSRF();
    
    // Fetch charts
    api.get('/plotly/').then(res => setCharts(res.data));
  }, []);

  const createChart = async (chartData) => {
    const response = await api.post('/plotly/', chartData);
    return response.data;
  };

  return <PlotlyChart data={charts} />;
}
```

## 📚 Documentation

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **CSRF Guide**: [CSRF_DOCUMENTATION.md](./CSRF_DOCUMENTATION.md)
- **Pydantic Models**: See [models.py](./models.py)

## 🐛 Troubleshooting

### Common Issues

**Issue: Can't connect to MongoDB**
```bash
# Check if MongoDB is running
mongo --eval "db.adminCommand('ping')"

# Start MongoDB
brew services start mongodb-community  # macOS
sudo systemctl start mongod            # Linux
```

**Issue: CORS errors**
- Ensure React app URL is in `CORS_ORIGINS` in `.env`
- Check `withCredentials: true` is set in axios config

**Issue: CSRF token errors**
- Verify `/csrf-token` is called before state-changing requests
- Check cookies are enabled in browser
- Ensure `withCredentials: true` in frontend

**Issue: Rate limit exceeded**
- Adjust `RATE_LIMIT_PER_MINUTE` in `.env`
- Check if you're making too many requests in development

## 📄 License

MIT License - feel free to use this project for learning and development.

## 👥 Contributing

This is a personal project for testing backend implementations. Feel free to fork and modify for your needs.

## 🔗 Related Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Python Driver](https://pymongo.readthedocs.io/)
- [Plotly.js Documentation](https://plotly.com/javascript/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [OWASP Security Guidelines](https://owasp.org/)

---

**Built with** ❤️ **using FastAPI, MongoDB, and Python**
