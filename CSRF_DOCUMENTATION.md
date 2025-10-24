# CSRF Protection Implementation Guide

## Overview

This FastAPI backend implements **CSRF (Cross-Site Request Forgery)** protection using the **synchronizer token pattern** (double-submit cookie method). This prevents malicious websites from making unauthorized requests on behalf of authenticated users.

## How It Works

### 1. Token Generation
- Client requests a CSRF token from `/csrf-token` endpoint
- Server generates a secure random token using `secrets.token_hex(32)`
- Token is stored server-side with timestamp
- Token is sent to client in two ways:
  - **Cookie**: `XSRF-TOKEN` (readable by JavaScript, `httponly=False`)
  - **Response body**: Confirms successful token generation

### 2. Token Validation
- For state-changing requests (POST, PUT, DELETE):
  - Client reads token from cookie
  - Client sends token in `X-CSRF-Token` header
  - Server validates both tokens match
  - Server checks token hasn't expired (24-hour TTL)

### 3. Security Flow

```
┌─────────┐                    ┌─────────┐
│ Client  │                    │ Server  │
└────┬────┘                    └────┬────┘
     │                              │
     │ GET /csrf-token              │
     ├─────────────────────────────>│
     │                              │ Generate token
     │                              │ Store: csrf_tokens[token] = timestamp
     │                              │
     │ Set-Cookie: XSRF-TOKEN=abc123│
     │<─────────────────────────────┤
     │ Response: {success: true}    │
     │                              │
     │ POST /plotly/                │
     │ Cookie: XSRF-TOKEN=abc123    │
     │ Header: X-CSRF-Token=abc123  │
     ├─────────────────────────────>│
     │                              │ Validate:
     │                              │ - Cookie == Header?
     │                              │ - Token exists?
     │                              │ - Not expired?
     │                              │
     │      Success Response        │
     │<─────────────────────────────┤
     │                              │
```

## Implementation Details

### Backend (Python/FastAPI)

#### 1. Dependencies & Imports

```python
from fastapi import Header, Cookie, HTTPException, Request, Depends
from typing import Optional
import secrets
import time
```

#### 2. Token Storage

```python
# In-memory storage (use Redis in production)
csrf_tokens: Dict[str, float] = {}
```

**Production Note**: Replace in-memory dict with Redis for:
- Distributed systems
- Horizontal scaling
- Persistence across restarts

#### 3. CSRF Validation Dependency

```python
async def validate_csrf(
    request: Request,
    xsrf_token: Optional[str] = Cookie(None, alias="XSRF-TOKEN"),
    x_csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token")
) -> None:
    """Validate CSRF token using synchronizer token pattern"""
    # Skip for safe methods
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return
    
    # Validate tokens exist and match
    if not xsrf_token or not x_csrf_token:
        raise HTTPException(status_code=403, detail="CSRF token missing")
    
    if xsrf_token != x_csrf_token:
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    
    # Validate token hasn't expired (24 hours)
    current_time = time.time()
    token_timestamp = csrf_tokens.get(xsrf_token, 0)
    if current_time - token_timestamp > 86400:
        raise HTTPException(status_code=403, detail="CSRF token expired")
```

#### 4. Token Generation Endpoint

```python
@app.get("/csrf-token")
async def get_csrf_token() -> JSONResponse:
    """Generate and return CSRF token"""
    token = secrets.token_hex(32)
    csrf_tokens[token] = time.time()
    
    # Clean up expired tokens
    current_time = time.time()
    expired = [t for t, ts in csrf_tokens.items() if current_time - ts > 86400]
    for t in expired:
        del csrf_tokens[t]
    
    response = JSONResponse({"success": True})
    response.set_cookie(
        key="XSRF-TOKEN",
        value=token,
        httponly=False,  # JavaScript must read this
        secure=False,    # Set True in production (HTTPS)
        samesite="lax",
        max_age=86400
    )
    return response
```

#### 5. Protected Routes

Apply CSRF validation to all state-changing endpoints:

```python
@app.post("/plotly/", dependencies=[Depends(validate_csrf)])
async def create_plotly_chart(chart_data: PlotlyDataCreate):
    # Route logic here
    pass

@app.put("/plotly/{item_id}", dependencies=[Depends(validate_csrf)])
async def update_plotly_chart(item_id: int, chart_data: PlotlyDataUpdate):
    # Route logic here
    pass

@app.delete("/plotly/{item_id}", dependencies=[Depends(validate_csrf)])
async def delete_plotly_chart(item_id: int):
    # Route logic here
    pass
```

#### 6. CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],  # Allow CSRF header
    expose_headers=["X-Total-Count"]
)
```

### Frontend (JavaScript/TypeScript)

#### Setup with Axios

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true,  // Required for cookies
});

// Helper: Get CSRF token from cookie
function getCsrfToken() {
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'XSRF-TOKEN') {
      return decodeURIComponent(value);
    }
  }
  return null;
}

// Request interceptor
api.interceptors.request.use((config) => {
  const method = config.method?.toUpperCase();
  
  // Add CSRF token for state-changing requests
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const token = getCsrfToken();
    if (token) {
      config.headers['X-CSRF-Token'] = token;
    }
  }
  
  return config;
});

// Response interceptor (auto-retry on CSRF failure)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 403 && !originalRequest._retry) {
      originalRequest._retry = true;
      await api.get('/csrf-token');
      return api.request(originalRequest);
    }
    
    return Promise.reject(error);
  }
);

export default api;
```

#### Initialize on App Start

```javascript
// In App.tsx or main.tsx
import { useEffect } from 'react';
import api from './api';

function App() {
  useEffect(() => {
    // Fetch initial CSRF token
    api.get('/csrf-token').catch(console.error);
  }, []);
  
  return <YourApp />;
}
```

## Testing

### Manual Testing

1. **Get CSRF Token**
   ```bash
   curl -c cookies.txt http://localhost:8000/csrf-token
   ```

2. **Extract Token from Cookie**
   ```bash
   TOKEN=$(grep XSRF-TOKEN cookies.txt | awk '{print $7}')
   ```

3. **Make Protected Request**
   ```bash
   curl -b cookies.txt \
     -H "X-CSRF-Token: $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     -d '{"data": [{"x": [1,2,3], "y": [1,2,3]}], "layout": {}}' \
     http://localhost:8000/plotly/
   ```

4. **Test Without Token (Should Fail)**
   ```bash
   curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"data": [], "layout": {}}' \
     http://localhost:8000/plotly/
   # Expected: 403 Forbidden
   ```

### Automated Tests (pytest)

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_csrf_protection():
    # Should fail without token
    response = client.post("/plotly/", json={"data": [], "layout": {}})
    assert response.status_code == 403
    
    # Get CSRF token
    response = client.get("/csrf-token")
    assert response.status_code == 200
    
    # Extract token from cookie
    csrf_cookie = response.cookies.get("XSRF-TOKEN")
    
    # Should succeed with token
    response = client.post(
        "/plotly/",
        json={"data": [], "layout": {}},
        cookies={"XSRF-TOKEN": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie}
    )
    assert response.status_code == 200
```

## Production Considerations

### 1. Use Redis for Token Storage

```python
import redis.asyncio as redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

async def store_csrf_token(token: str):
    await redis_client.setex(f"csrf:{token}", 86400, "1")

async def validate_csrf_token(token: str) -> bool:
    exists = await redis_client.exists(f"csrf:{token}")
    return exists == 1
```

### 2. Enable HTTPS

```python
response.set_cookie(
    key="XSRF-TOKEN",
    value=token,
    httponly=False,
    secure=True,        # Require HTTPS
    samesite="strict",  # Stricter in production
    max_age=86400
)
```

### 3. Environment Configuration

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    csrf_secret_key: str
    csrf_token_expiry: int = 86400
    cookie_secure: bool = True
    cookie_samesite: str = "strict"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 4. Rate Limiting

Add rate limiting to `/csrf-token` endpoint to prevent token generation abuse:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/csrf-token")
@limiter.limit("10/minute")
async def get_csrf_token(request: Request):
    # Implementation
    pass
```

## Security Best Practices

✅ **DO:**
- Use `secrets` module for token generation
- Set `httponly=False` only for XSRF-TOKEN (must be readable by JS)
- Use `secure=True` in production (HTTPS only)
- Set appropriate token expiration (24 hours recommended)
- Log CSRF failures for security monitoring
- Clean up expired tokens regularly
- Use Redis/database for distributed systems

❌ **DON'T:**
- Don't reuse tokens across sessions
- Don't store tokens in localStorage (use cookies)
- Don't skip CSRF validation for authenticated routes
- Don't use predictable token values
- Don't expose tokens in URLs or logs
- Don't set overly long expiration times

## Troubleshooting

### Issue: "CSRF token missing"
- **Cause**: Frontend not sending cookie or header
- **Fix**: Ensure `withCredentials: true` in axios config

### Issue: "Invalid CSRF token"
- **Cause**: Cookie and header values don't match
- **Fix**: Verify token extraction logic in frontend

### Issue: "CSRF token expired"
- **Cause**: Token older than 24 hours
- **Fix**: Call `/csrf-token` to refresh

### Issue: CORS errors
- **Cause**: Missing CSRF header in CORS config
- **Fix**: Add `X-CSRF-Token` to `allow_headers`

## References

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [FastAPI Security Guide](https://fastapi.tiangolo.com/tutorial/security/)
- [Double Submit Cookie Pattern](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#double-submit-cookie)

## Support

For issues or questions about this CSRF implementation, please refer to:
- Project documentation
- Security team contact
- Backend API maintainers
