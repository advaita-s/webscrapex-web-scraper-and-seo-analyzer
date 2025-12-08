from .models import ScrapeJob
from .database import get_session
from sqlmodel import select
from datetime import datetime
import json
import os
import csv
from typing import Optional, Dict, Any

# output dir can be configured via SCRAPE_OUTPUT_DIR env var; fallback to app/outputs
DEFAULT_OUTPUT_DIR = os.getenv("SCRAPE_OUTPUT_DIR", None)
if not DEFAULT_OUTPUT_DIR:
    # directory relative to this file: ../outputs
    DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
# ensure directory exists
os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)


def create_job(url: str, selectors: dict = None):
    session = get_session()
    job = ScrapeJob(url=url, selectors=json.dumps(selectors) if selectors else None, status="pending")
    session.add(job)
    session.commit()
    session.refresh(job)
    session.close()
    return job


def set_job_status(job_id: int, status: str, result=None, error: str = None):
    session = get_session()
    job = session.get(ScrapeJob, job_id)
    if not job:
        session.close()
        return None
    job.status = status
    if result is not None:
        # ensure we store JSON serializable object
        try:
            job.result = result
        except Exception:
            # fallback: store as JSON string
            job.result = json.dumps(result)
    if error:
        job.error = error
    if status in ("done", "failed"):
        job.finished_at = datetime.utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)
    session.close()
    return job


def get_job(job_id: int):
    session = get_session()
    job = session.get(ScrapeJob, job_id)
    session.close()
    return job


def list_jobs(limit: int = 50):
    session = get_session()
    statement = select(ScrapeJob).order_by(ScrapeJob.created_at.desc()).limit(limit)
    results = session.exec(statement).all()
    session.close()
    return results


# ----------------- New helpers -----------------


def _result_to_csv_content(result: Dict[str, Any]) -> Optional[str]:
    """
    Convert a result dict into CSV string content.
    The result dict typically has keys like title, paragraphs (list), bulleted_features (list), price, etc.
    This function will flatten arrays into columns and produce CSV text.
    Returns CSV content string or None if nothing to write.
    """
    if not result or not isinstance(result, dict):
        return None

    # Build columns from keys
    cols = list(result.keys())
    # Build rows: determine max length among list columns
    max_rows = 1
    for k in cols:
        v = result.get(k)
        if isinstance(v, list):
            max_rows = max(max_rows, len(v))

    rows = []
    for r in range(max_rows):
        row = []
        for k in cols:
            v = result.get(k)
            if isinstance(v, list):
                cell = v[r] if r < len(v) else ""
                # replace newlines
                row.append(str(cell).replace("\n", " ").strip())
            elif isinstance(v, dict):
                row.append(json.dumps(v))
            else:
                row.append(str(v).replace("\n", " ").strip() if r == 0 else "")
        rows.append(row)

    # Build CSV string
    output_lines = []
    # header
    output_lines.append(",".join([f'"{c}"' for c in cols]))
    for row in rows:
        safe_cells = ['"{}"'.format(str(cell).replace('"', '""')) for cell in row]
        output_lines.append(",".join(safe_cells))
    return "\n".join(output_lines)


def _save_csv_file(job_id: int, result: Dict[str, Any]) -> Optional[str]:
    """
    Save result to a CSV file under DEFAULT_OUTPUT_DIR, return the absolute path or None on failure.
    Filename pattern: scrape_<job_id>_<timestamp>.csv
    """
    try:
        csv_content = _result_to_csv_content(result)
        if not csv_content:
            return None
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        filename = f"scrape_{job_id}_{timestamp}.csv"
        full_path = os.path.join(DEFAULT_OUTPUT_DIR, filename)
        with open(full_path, "w", encoding="utf-8", newline="") as f:
            f.write(csv_content)
        return full_path
    except Exception:
        # don't raise here; caller will handle errors
        return None


def save_result_for_job(job_id: int, result: Dict[str, Any], save_csv: bool = False) -> Optional[ScrapeJob]:
    """
    Store the result dict into the job.result column. Optionally save a CSV file and
    include its path into the saved result under the 'csv' key.
    Returns the updated job object or None if job not found.
    """
    session = get_session()
    job = session.get(ScrapeJob, job_id)
    if not job:
        session.close()
        return None

    # ensure result is JSON-serializable: don't modify input in-place
    result_copy = result.copy() if isinstance(result, dict) else {"data": result}

    # Save CSV if requested
    if save_csv:
        csv_path = _save_csv_file(job_id, result_copy)
        if csv_path:
            # store relative path if inside project, else absolute
            result_copy["csv"] = csv_path

    # store result directly (SQLModel/JSON column should accept dict; if not, convert)
    try:
        job.result = result_copy
    except Exception:
        job.result = json.dumps(result_copy)

    job.status = "done"
    job.finished_at = datetime.utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)
    session.close()
    return job


def delete_job(job_id: int) -> bool:
    session = get_session()
    job = session.get(ScrapeJob, job_id)
    if not job:
        session.close()
        return False

    # remove csv if exists
    csv_path = None
    if isinstance(job.result, dict):
        csv_path = job.result.get("csv")
    if csv_path and os.path.exists(csv_path):
        try:
            os.remove(csv_path)
        except:
            pass

    session.delete(job)
    session.commit()
    session.close()
    return True

