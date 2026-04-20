import httpx
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
API_KEY = os.getenv("API_KEY", "nas")

class AgentPdfService:
    """Wrapper for the ResearchDoi API PDF resolver."""
    
    async def resolve_pdf(self, doi: str, uid: str = "api-key-user") -> Optional[str]:
        url = f"{API_BASE_URL}/api/pdf/resolve"
        params = {"doi": doi}
        headers = {
            "X-Api-Key": API_KEY,
            "X-User-Id": uid
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("pdf_url")
                logger.error(f"[AgentPdfService] Error {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            logger.error(f"[AgentPdfService] Connection error: {e}")
            return None

pdf_service = AgentPdfService()
