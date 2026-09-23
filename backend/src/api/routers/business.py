import os
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Body, Query, HTTPException

from src.database.db_manager import db_manager

router = APIRouter(prefix="/api/business", tags=["Business Analytics & Branch Management"])

@router.get("/dashboard")
async def get_business_dashboard(
    business_id: Optional[int] = Query(None, description="Business or branch ID"),
    date: Optional[str] = Query(None, description="Date filter (YYYY-MM-DD)")
):
    """
    Returns high-level business intelligence metrics:
    - Customer vehicle footfall & demographics
    - Peak shopping/operating arrival hours
    - Hourly traffic distribution
    - Branch CCTV camera status
    """
    try:
        b_id = business_id if isinstance(business_id, int) else None
        t_date = date if isinstance(date, str) else None
        analytics = db_manager.get_business_dashboard_analytics(business_id=b_id, target_date=t_date)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการดึงข้อมูลธุรกิจ: {str(e)}")

@router.get("/companies")
async def list_businesses():
    """
    Lists all registered businesses, retail malls, stations, and branches.
    """
    businesses = db_manager.get_businesses()
    return {"status": "success", "businesses": businesses}

@router.post("/companies")
async def create_business_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Registers a new business entity or branch.
    The user can fill in their own business information here.
    """
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="กรุณาระบุชื่อธุรกิจหรือชื่อสาขา")

    business_type = payload.get("business_type", "retail")
    branch_code = payload.get("branch_code", "")
    address = payload.get("address", "")
    contact_email = payload.get("contact_email", "")
    contact_phone = payload.get("contact_phone", "")
    opening_hour = int(payload.get("opening_hour", 8))
    closing_hour = int(payload.get("closing_hour", 22))
    target_hourly_traffic = int(payload.get("target_hourly_traffic", 100))

    try:
        bid = db_manager.create_business(
            name=name,
            business_type=business_type,
            branch_code=branch_code,
            address=address,
            contact_email=contact_email,
            contact_phone=contact_phone,
            opening_hour=opening_hour,
            closing_hour=closing_hour,
            target_hourly_traffic=target_hourly_traffic
        )
        return {
            "status": "success",
            "message": f"เพิ่มข้อมูลธุรกิจ '{name}' สำเร็จเรียบร้อยแล้ว",
            "business_id": bid
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการบันทึกข้อมูลธุรกิจ: {str(e)}")

@router.put("/companies/{business_id}")
async def update_business_endpoint(business_id: int, payload: Dict[str, Any] = Body(...)):
    """
    Updates business or branch details.
    """
    success = db_manager.update_business(business_id, payload)
    if not success:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลธุรกิจที่ต้องการแก้ไข")
    return {"status": "success", "message": "อัปเดตข้อมูลธุรกิจสำเร็จ"}

@router.delete("/companies/{business_id}")
async def delete_business_endpoint(business_id: int):
    """
    Deletes a business and associated camera entries.
    """
    success = db_manager.delete_business(business_id)
    if not success:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลธุรกิจที่ต้องการลบ")
    return {"status": "success", "message": "ลบข้อมูลธุรกิจสำเร็จ"}

@router.get("/cameras")
async def list_business_cameras(business_id: Optional[int] = Query(None)):
    """
    Lists CCTV cameras associated with business branches.
    """
    cameras = db_manager.get_business_cameras(business_id=business_id)
    return {"status": "success", "cameras": cameras}

@router.post("/cameras")
async def create_business_camera_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Links a CCTV camera or RTSP stream to a business branch.
    The user can fill in their own camera details and stream URL here.
    """
    business_id = payload.get("business_id")
    name = payload.get("name", "").strip()
    stream_url = payload.get("stream_url", "").strip()
    camera_type = payload.get("camera_type", "entrance")
    location_note = payload.get("location_note", "")

    if not business_id:
        raise HTTPException(status_code=400, detail="กรุณาเลือกสาขาธุรกิจที่ต้องการเชื่อมโยงกล้อง")
    if not name or not stream_url:
        raise HTTPException(status_code=400, detail="กรุณาระบุชื่อกล้องและ URL สัญญาณกล้อง CCTV / RTSP")

    try:
        cid = db_manager.create_business_camera(
            business_id=int(business_id),
            name=name,
            stream_url=stream_url,
            camera_type=camera_type,
            location_note=location_note
        )
        return {
            "status": "success",
            "message": f"เชื่อมต่อกล้อง '{name}' เข้ากับธุรกิจสำเร็จ",
            "camera_id": cid
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการบันทึกกล้อง: {str(e)}")

@router.delete("/cameras/{camera_id}")
async def delete_business_camera_endpoint(camera_id: int):
    """
    Removes a CCTV camera from business.
    """
    success = db_manager.delete_business_camera(camera_id)
    if not success:
        raise HTTPException(status_code=404, detail="ไม่พบกล้องที่ต้องการลบ")
    return {"status": "success", "message": "ลบกล้องสำเร็จ"}
