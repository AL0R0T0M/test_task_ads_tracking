from pydantic import BaseModel, Field
from typing import List, Any

class CampaignCreate(BaseModel):
    name: str = Field(..., description="The name of the campaign.")
    country_codes: List[str] = Field(..., description="List of ISO 3166-1 alpha-2 country codes (e.g., ['US', 'RU']).")
    offer_id: int = Field(..., gt=0, description="The ID of the Keitaro offer.")


class CampaignResponse(BaseModel):
    id: int
    name: str
    alias: str


class StreamsUpdateRequest(BaseModel):
    streams: List[Any]