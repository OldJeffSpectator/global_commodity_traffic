"""FastAPI application entry point."""
import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.api.routes import router
from app.db.seed import init_db

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

app = FastAPI(title="Global Commodity Traffic API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:16668", "http://127.0.0.1:16668"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {"message": "Global Commodity Traffic API", "version": "1.0.0"}


@app.get("/api/countries-geojson")
def countries_geojson():
    geojson_path = os.path.join(DATA_DIR, "countries.geojson")
    return FileResponse(geojson_path, media_type="application/json")
