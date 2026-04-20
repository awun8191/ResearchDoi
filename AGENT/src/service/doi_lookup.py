import httpx
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
API_KEY = os.getenv("API_KEY", "nas")

class AgentDoiService:
    """Wrapper for the ResearchDoi API DOI resolver."""
    
    async def fetch_metadata(self, doi: str, uid: str = "api-key-user") -> Optional[Dict[str, Any]]:
        url = f"{API_BASE_URL}/api/doi/{doi}"
        headers = {
            "X-Api-Key": API_KEY,
            "X-User-Id": uid
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    return resp.json()
                logger.error(f"[AgentDoiService] Error {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            logger.error(f"[AgentDoiService] Connection error: {e}")
            return None

doi_service = AgentDoiService()
