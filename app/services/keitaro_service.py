import requests
from fastapi import HTTPException, status
from app.core.config import settings
from functools import lru_cache


class KeitaroService:
    def __init__(self):
        self.api_url = settings.KEITARO_API_URL.rstrip("/")
        self.headers = {"Api-Key": settings.KEITARO_API_KEY}

    def _make_request(self, method: str, endpoint: str, json_data: dict | None = None):
        """Helper to make requests to Keitaro API."""
        try:
            response = requests.request(
                method,
                f"{self.api_url}/{endpoint}",
                headers=self.headers,
                json=json_data,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            error_details = "No details from API."
            try:
                error_details = http_err.response.json()
            except requests.exceptions.JSONDecodeError:
                pass
            raise HTTPException(
                status_code=http_err.response.status_code,
                detail=f"Keitaro API error: {http_err}. Details: {error_details}",
            )
        except requests.exceptions.RequestException as req_err:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error connecting to Keitaro API: {req_err}",
            )

    def get_default_domain_id(self) -> int:
        """Fetches domains and returns the ID of the first one."""
        domains = self._make_request("GET", "domains")
        if not domains:
            raise HTTPException(status_code=404, detail="No domains found in Keitaro.")
        return domains[0]["id"]

    def get_default_group_id(self) -> int:
        """Fetches campaign groups and returns the ID of the first one."""
        groups = self._make_request("GET", "groups?type=campaigns")
        if not groups:
            raise HTTPException(status_code=404, detail="No campaign groups found in Keitaro.")
        return groups[0]["id"]

    def get_default_source_id(self) -> int:
        """Fetches traffic sources and returns the ID of the first one."""
        sources = self._make_request("GET", "traffic_sources")
        if not sources:
            raise HTTPException(status_code=404, detail="No traffic sources found in Keitaro.")
        return sources[0]["id"]

    def create_campaign(self, payload: dict):
        """Creates a campaign in Keitaro."""
        payload.pop("streams", None)
        return self._make_request("POST", "campaigns", json_data=payload)

    def get_campaign(self, campaign_id: int):
        """
        Fetches a single campaign by its ID and separately fetches its streams, then
        combines them into one object.
        """
        campaign_data = self._make_request("GET", f"campaigns/{campaign_id}")
        streams_data = self._make_request("GET", f"campaigns/{campaign_id}/streams")
        campaign_data["streams"] = streams_data
        return campaign_data

    def get_campaigns(self):
        """Fetches all campaigns."""
        return self._make_request("GET", "campaigns")

    def get_offers(self):
        """Fetches all available offers."""
        return self._make_request("GET", "offers")

    def get_campaign_streams(self, campaign_id: int):
        """[Diagnostics] Fetches only the streams for a campaign."""
        return self._make_request("GET", f"campaigns/{campaign_id}/streams")

    def update_campaign_streams(self, campaign_id: int, streams: list):
        """Updates the streams of a specific campaign."""
        payload = {"streams": streams}
        return self._make_request("PUT", f"campaigns/{campaign_id}", json_data=payload)

@lru_cache()
def get_keitaro_service() -> KeitaroService:
    return KeitaroService()