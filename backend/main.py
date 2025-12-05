import collections
import collections.abc
collections.MutableMapping = collections.abc.MutableMapping
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, market, chat
from mcp_handlers.router import router as mcp_router
from database import engine, Base
from worker import fetch_all_regions_orders
import os
from fastapi_pagination import add_pagination, Page

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor

app = FastAPI(title="Lenny API")

# Setup OpenTelemetry
if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    resource = Resource(attributes={
        SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "lenny-backend")
    })
    trace.set_tracer_provider(TracerProvider(resource=resource))
    
    # OTLP Exporter
    otlp_exporter = OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
    
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    # Instrument Celery (for task production)
    CeleryInstrumentor().instrument()

# CORS
app.add_middleware(
    CORSMiddleware,
    # During local development allow all origins. In production restrict this.
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(market.router)
app.include_router(chat.router)
app.include_router(mcp_router)

# Configure pagination with max 50 items per page and max 250 total items (5 pages)
Page.__params__ = {"size": 50, "max_size": 250}
add_pagination(app)

@app.on_event("startup")
async def startup():
    # Create tables (for dev only - use Alembic in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Trigger initial fetch
    fetch_all_regions_orders.delay()

@app.get("/")
async def root():
    return {"message": "Hello from Lenny EVE Online Market Dashboard"}
