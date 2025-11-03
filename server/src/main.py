from fastapi import FastAPI, Depends, HTTPException, status, Header
from .config import settings
from .models import IngestData
from .mq_client import publish_message
from typing import Optional

app = FastAPI(
    title="Distributed Resource Monitoring Server",
    description="API for ingesting metrics from agents."
)

# --- Security Dependency ---

def get_api_key(authorization: Optional[str] = Header(None)) -> str:
    """
    Dependency to check for a valid Bearer token in the Authorization header.
    """
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    parts = authorization.split()
    
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Use 'Bearer <key>'"
        )
    
    token = parts[1]
    
    if token != settings.AGENT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )
    return token

# --- API Endpoints ---

@app.get("/health", tags=["General"])
async def health_check():
    """A simple health check endpoint."""
    return {"status": "ok"}

@app.post("/v1/data/ingest", status_code=status.HTTP_202_ACCEPTED, tags=["Ingestion"])
async def ingest_data(
    data: IngestData, 
    api_key: str = Depends(get_api_key)
):
    """
    Asynchronous endpoint to receive metrics data from agents.
    It validates the top-level structure and publishes to the message queue.
    """
    try:
        # Publish the raw dictionary to the queue
        # The worker will handle the detailed parsing
        success = publish_message(data.model_dump())
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Message queue is currently unavailable. Please retry later."
            )
            
        return {"status": "accepted"}
        
    except Exception as e:
        print(f"Error in ingestion endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred."
        )