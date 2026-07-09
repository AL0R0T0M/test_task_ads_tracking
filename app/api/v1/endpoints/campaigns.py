from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import re
import time
from app.schemas.campaign import CampaignCreate, CampaignResponse, StreamsUpdateRequest
from app.schemas.offer import Offer, OfferUpdateRequest
from app.services.keitaro_service import KeitaroService, get_keitaro_service
from app.db.session import get_db
from app.models.action_log import ActionLog

router = APIRouter()


@router.post(
    "/campaigns",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    campaign_data: CampaignCreate,
    keitaro: KeitaroService = Depends(get_keitaro_service),
    db: Session = Depends(get_db),
):
    """
    Creates a new campaign in Keitaro with two streams:
    1. A stream that filters traffic from a specific country and redirects to Google.
    2. A default stream that redirects to a specified offer.
    """
    try:
        domain_id = keitaro.get_default_domain_id()
        group_id = keitaro.get_default_group_id()
        source_id = keitaro.get_default_source_id()

        base_alias = re.sub(r'[^a-z0-9]+', '-', campaign_data.name.lower()).strip('-')
        alias = f"{base_alias}-{int(time.time())}"

        empty_campaign_payload = {
            "name": campaign_data.name,
            "domain_id": domain_id,
            "alias": alias,
            "group_id": group_id,
            "traffic_source_id": source_id,
        }
        created_campaign = keitaro.create_campaign(empty_campaign_payload)
        campaign_id = created_campaign["id"]

        streams_to_add = [
            {
                "name": f"{', '.join(campaign_data.country_codes)} users -> Google",
                "schema": "redirect",
                "action_type": "http",
                "action_payload": "https://google.com",
                "filters": [{"name": "country", "mode": "accept", "payload": campaign_data.country_codes}],
                "state": "active",
            },
            {
                "name": "Default offer distribution",
                "schema": "landings",
                "action_type": "http",
                "action_payload": "",
                "offers": [{"offer_id": campaign_data.offer_id, "share": 100}],
                "state": "active",
            },
        ]

        keitaro.update_campaign_streams(campaign_id, streams_to_add)

        final_campaign = keitaro.get_campaign(campaign_id)

        log_entry = ActionLog(
            action="create_campaign",
            campaign_id=campaign_id,
            details=f"Campaign '{final_campaign['name']}' created.",
        )
        db.add(log_entry)
        db.commit()

        return final_campaign
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.get("/offers", response_model=list[Offer], tags=["Offers"])
async def list_offers(keitaro: KeitaroService = Depends(get_keitaro_service)):
    """
    Get a list of all available offers from Keitaro.
    """
    return keitaro.get_offers()


@router.get("/campaigns/{campaign_id}", response_model=dict, tags=["Keitaro Diagnostics"])
async def get_campaign_details(
    campaign_id: int,
    keitaro: KeitaroService = Depends(get_keitaro_service),
):
    """
    [Diagnostics] Fetches the full details of an existing campaign from Keitaro.

    Use this to inspect the structure of a working campaign and find the correct
    values for fields like 'action_type'.
    """
    try:
        campaign_details = keitaro.get_campaign(campaign_id)
        return campaign_details
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.get("/campaigns/{campaign_id}/streams", response_model=list, tags=["Keitaro Diagnostics"])
async def get_campaign_streams_details(
    campaign_id: int,
    keitaro: KeitaroService = Depends(get_keitaro_service),
):
    """
    [Diagnostics] Fetches just the streams array for an existing campaign.

    Use this to inspect the structure of a working campaign's streams and find
    the correct values for fields like 'action_type'.
    """
    try:
        streams = keitaro.get_campaign_streams(campaign_id)
        return streams
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )

@router.get("/campaigns", response_model=list[CampaignResponse], tags=["Campaigns"])
async def list_campaigns(keitaro: KeitaroService = Depends(get_keitaro_service)):
    """
    Get a list of all campaigns from Keitaro.
    """
    return keitaro.get_campaigns()


@router.put("/campaigns/{campaign_id}", response_model=dict, tags=["Campaign Editor"])
async def update_campaign(
    campaign_id: int,
    request: StreamsUpdateRequest,
    keitaro: KeitaroService = Depends(get_keitaro_service),
    db: Session = Depends(get_db),
):
    """
    Updates the streams for a specific campaign.
    """
    try:
        updated_campaign = keitaro.update_campaign_streams(campaign_id, request.streams)

        log_entry = ActionLog(
            action="update_streams",
            campaign_id=campaign_id,
            details=f"Streams for campaign {campaign_id} updated.",
        )
        db.add(log_entry)
        db.commit()

        return updated_campaign
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while updating campaign: {str(e)}",
        )