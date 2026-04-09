from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Naya CORS feature
import asyncio
from contextlib import asynccontextmanager

from . import models
from .database import engine
from .routes import router
from .monitor import start_monitoring

# Database tables create karna
models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run the monitoring system in the background
    task = asyncio.create_task(start_monitoring())
    yield
    # Shutdown logic
    task.cancel()

app = FastAPI(title="SmartCity Service Desk", lifespan=lifespan)

# 🔥 CORS CONFIGURATION (Taki HTML page API se baat kar sake) 🔥
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes add karna
app.include_router(router, prefix="/api/v1", tags=["Tickets"])

@app.get("/")
def root():
    return {"message": "SmartCity Ticket System is Running! Go to /docs for API documentation."}