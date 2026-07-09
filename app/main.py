from fastapi import FastAPI, Request
from app.api.v1.endpoints import campaigns
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(
    title="Ads Tracking Test Task",
    description="An application to manage Keitaro campaigns.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(campaigns.router, prefix="/api/v1")


@app.get("/")
async def read_root(request: Request):
    """
    Serves the main HTML page.
    """
    return templates.TemplateResponse("index.html", {"request": request})