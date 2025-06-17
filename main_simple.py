"""Simplified main.py for Synology compatibility"""
from main import app
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Starting server on port {port}...")
    
    # Minimal uvicorn config
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        access_log=True,
        log_level="info"
    )