# backend/app/main.py
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import json

# --- load .env explicitly from backend directory so OPENAI_API_KEY is picked up ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path)

# --- app-specific imports (import after env load if they depend on env) ---
from .seo import router as seo_router
from .database import init_db
from .crud import create_job, get_job, list_jobs
from .scraper import run_scrape_job
from .schemas import ScrapeRequest, ScrapeResponse, ResultResponse

app = FastAPI(title="Web Scraper API")

# --- CORS middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mount SEO router here so /api/seo routes are available ---
app.include_router(seo_router, prefix="/api/seo")


@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/api/scrape", response_model=ScrapeResponse)
def create_scrape(scrape: ScrapeRequest, background_tasks: BackgroundTasks):
    job = create_job(scrape.url, selectors=scrape.selectors)
    background_tasks.add_task(
        run_scrape_job,
        job.id,
        scrape.url,
        scrape.selectors,
        scrape.save_csv,
        scrape.ai_summary,
    )
    return {"id": job.id, "status": job.status}


@app.get("/api/results/{job_id}", response_model=ResultResponse)
def get_results(job_id: int):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "url": job.url,
        "status": job.status,
        "result": job.result,
        "error": job.error,
    }


@app.get("/api/jobs")
def get_jobs():
    jobs = list_jobs()
    return [
        {"id": j.id, "url": j.url, "status": j.status, "created_at": j.created_at.isoformat()}
        for j in jobs
    ]


@app.get("/api/results/{job_id}/csv")
def get_csv(job_id: int):
    job = get_job(job_id)
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="CSV not found")
    # job.result should include "csv" path when save_csv_flag used
    csv_path = None
    if isinstance(job.result, dict):
        csv_path = job.result.get("csv")
    if not csv_path or not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="CSV file not available")
    return FileResponse(csv_path, media_type="text/csv", filename=os.path.basename(csv_path))


@app.get("/debug/key")
def debug_key():
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return {"exists": True, "prefix": key[:8] + "..."}
    return {"exists": False, "prefix": None}


@app.delete("/api/jobs/{job_id}")
def delete_job_endpoint(job_id: int):
    from . import crud

    deleted = crud.delete_job(job_id)
    if not deleted:
        return Response(status_code=404)
    return Response(status_code=204)
