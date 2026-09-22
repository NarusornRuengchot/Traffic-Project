import datetime
from typing import Optional
from fastapi import APIRouter, Query, Response
from src.database.db_manager import db_manager

router = APIRouter(prefix="/api/reports", tags=["Reports & Analytics"])

def _clean_param(param, default=None):
    if param is None or hasattr(param, "default") or str(param) in ("all", "All", "None", ""):
        return default
    return str(param)

@router.get("/peak-hours")
async def get_peak_hours_report(date: Optional[str] = Query(None)):
    """Returns 24h hourly volume and peak-hours analytics for the selected date."""
    target_date = _clean_param(date)
    return db_manager.get_peak_hours_analysis(target_date)

@router.get("/history")
async def get_history_report(
    date: Optional[str] = Query(None),
    vehicle_type: Optional[str] = Query("All"),
    direction: Optional[str] = Query("All"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200)
):
    """Returns paginated vehicle crossing history with filters."""
    target_date = _clean_param(date)
    v_type = _clean_param(vehicle_type, default="All")
    dir_str = _clean_param(direction, default="All")
    p = 1 if hasattr(page, "default") else int(page)
    lim = 50 if hasattr(limit, "default") else int(limit)

    offset = (p - 1) * lim
    events, total = db_manager.get_events_history(
        limit=lim,
        offset=offset,
        target_date=target_date,
        vehicle_type=v_type,
        direction=dir_str
    )
    return {
        "events": events,
        "total": total,
        "page": p,
        "limit": lim,
        "total_pages": (total + lim - 1) // lim if total > 0 else 1
    }

@router.get("/dates")
async def get_report_dates():
    """Returns list of distinct dates available in the database."""
    dates = db_manager.get_available_dates()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    if today not in dates:
        dates.insert(0, today)
    return {"dates": dates}

@router.get("/export")
async def export_report_csv(date: Optional[str] = Query(None)):
    """Generates downloadable CSV export from SQLite database."""
    target_date = _clean_param(date)
    csv_str = db_manager.export_csv(target_date)
    filename = f"traffic_report_{target_date or 'all'}.csv"
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/incidents")
async def get_incidents_report(
    date: Optional[str] = Query(None),
    incident_type: Optional[str] = Query("All"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200)
):
    """Returns paginated traffic incidents with filtering."""
    target_date = _clean_param(date)
    inc_type = _clean_param(incident_type, default="All")
    p = 1 if hasattr(page, "default") else int(page)
    lim = 50 if hasattr(limit, "default") else int(limit)

    offset = (p - 1) * lim
    incidents, total = db_manager.get_incidents_history(
        limit=lim,
        offset=offset,
        target_date=target_date,
        incident_type=inc_type
    )
    return {
        "incidents": incidents,
        "total": total,
        "page": p,
        "limit": lim,
        "total_pages": (total + lim - 1) // lim if total > 0 else 1
    }

@router.get("/speed")
async def get_speed_report(date: Optional[str] = Query(None)):
    """Returns average, peak, and modal speed distribution statistics."""
    target_date = _clean_param(date)
    return db_manager.get_speed_analytics(target_date)
