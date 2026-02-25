from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from modules.entity import *
from modules.logger import get_logger
from routers import *

load_dotenv()

logger = get_logger("APP")

app = FastAPI(
    title="Cargo Emissions Tracker API",
    description="API for calculating carbon emissions and optimal routes for cargo transportation.",
    version="1.0.0",
    debug=os.getenv("DEBUG", "True").lower() in ("true", "1", "t"),
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for frontend
app.mount("/static", StaticFiles(directory="public"), name="static")

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/user", tags=["User Operations"])
app.include_router(route_router, prefix="/api/routes", tags=["Route Calculation"])
app.include_router(search_history_router, prefix="/api/history", tags=["Search History"])


@app.get(
    "/ping",
    summary="Health check",
    description="Health check endpoint.",
    response_class=JSONResponse,
)
async def ping():
    """Health check endpoint."""
    return JSONResponse({"ping": "pong"}, status.HTTP_200_OK)


@app.get("/")
async def root():
    """Serve the main frontend page."""
    from fastapi.responses import FileResponse

    return FileResponse("public/index.html")
