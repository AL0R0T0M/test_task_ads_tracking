from pydantic import BaseModel


class Offer(BaseModel):
    id: int
    name: str


class OfferUpdateRequest(BaseModel):
    offer_id: int