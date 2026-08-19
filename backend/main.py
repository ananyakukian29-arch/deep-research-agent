import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router

app = FastAPI(title="Deep Research API", version="1.0.0")

# Set local development URLs as the baseline
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Dynamically inject the production frontend URL if it exists
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    # rstrip("/") ensures no trailing slashes break the CORS string match
    origins.append(frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
def health_check():
    return {"status": "Production Backend is Online"}