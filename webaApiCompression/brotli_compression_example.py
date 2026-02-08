# main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.gzip import GZipMiddleware
import brotli
from starlette.middleware.base import BaseHTTPMiddleware
import time

app = FastAPI()

# Add Gzip middleware (built-in)
# app.add_middleware(GZipMiddleware, minimum_size=1000)  # Only compress responses > 1KB


# Custom Brotli middleware
class BrotliMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Check if client accepts brotli
        accept_encoding = request.headers.get("accept-encoding", "")
        
        if "br" in accept_encoding:
            # Get response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Only compress if body is large enough (similar to GZipMiddleware threshold)
            if len(body) >= 1000:
                # Compress with brotli (quality 4 is good balance)
                compressed_body = brotli.compress(body, quality=4)
                
                # Return compressed response
                # Remove original Content-Length header to avoid conflicts
                headers = dict(response.headers)
                headers.pop("content-length", None)
                
                return Response(
                    content=compressed_body,
                    media_type=response.media_type,
                    headers={
                        **headers,
                        "Content-Encoding": "br",
                        "Content-Length": str(len(compressed_body))
                    }
                )
        
        return response

# Uncomment to use Brotli instead of Gzip
app.add_middleware(BrotliMiddleware)


# Example endpoints
@app.get("/small")
async def small_response():
    """Small response - won't be compressed (< 1KB)"""
    return {"message": "Hello World"}


@app.get("/large")
async def large_response():
    """Large response - will be compressed"""
    # Generate ~50KB of data
    data = {
        "users": [
            {
                "id": i,
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "bio": "A" * 100,  # Repetitive text compresses well
                "metadata": {
                    "created_at": "2024-01-01",
                    "tags": ["tag1", "tag2", "tag3"],
                    "settings": {"theme": "dark", "notifications": True}
                }
            }
            for i in range(500)
        ]
    }
    return data


@app.get("/benchmark")
async def benchmark_compression():
    """Compare compression ratios"""
    import json
    import gzip
    
    # Sample data
    data = {
        "items": [{"id": i, "data": "x" * 100} for i in range(1000)]
    }
    
    # Original size
    original = json.dumps(data).encode()
    original_size = len(original)
    
    # Gzip compression
    gzip_compressed = gzip.compress(original, compresslevel=6)
    gzip_size = len(gzip_compressed)
    
    # Brotli compression
    brotli_compressed = brotli.compress(original, quality=4)
    brotli_size = len(brotli_compressed)
    
    return {
        "original_bytes": original_size,
        "gzip": {
            "bytes": gzip_size,
            "ratio": f"{(1 - gzip_size/original_size) * 100:.1f}%"
        },
        "brotli": {
            "bytes": brotli_size,
            "ratio": f"{(1 - brotli_size/original_size) * 100:.1f}%"
        }
    }


# Test endpoint to see response headers
@app.get("/headers")
async def check_headers(request: Request):
    """See what compression your client supports"""
    return {
        "accept-encoding": request.headers.get("accept-encoding", "none"),
        "user-agent": request.headers.get("user-agent", "unknown")
    }