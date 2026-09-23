import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Body, Header, HTTPException, Depends

from src.database.db_manager import db_manager
from src.utils.security import create_access_token, verify_access_token

router = APIRouter(prefix="/api/auth", tags=["User Authentication & Roles"])

def get_current_user_from_header(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """Extracts and verifies JWT token from Authorization: Bearer <token> header."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    payload = verify_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user = db_manager.get_user_by_id(payload["sub"])
    return user

@router.post("/register")
async def register_user(payload: Dict[str, Any] = Body(...)):
    """
    Registers a new user account.
    """
    username = payload.get("username", "").strip()
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    full_name = payload.get("full_name", "").strip()
    # Public registration must never be able to self-assign admin privileges.
    role = "user"
    business_id = payload.get("business_id")

    if not username or len(username) < 3:
        raise HTTPException(status_code=400, detail="ชื่อผู้ใช้ (Username) ต้องมีความยาวอย่างน้อย 3 ตัวอักษร")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="รูปแบบอีเมลไม่ถูกต้อง")
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร")

    if db_manager.get_user_by_username(username):
        raise HTTPException(status_code=400, detail="ชื่อผู้ใช้นี้ถูกใช้งานแล้วในระบบ")
    if db_manager.get_user_by_email(email):
        raise HTTPException(status_code=400, detail="อีเมลนี้ถูกใช้งานแล้วในระบบ")

    try:
        user = db_manager.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role=role,
            business_id=business_id
        )
        token = create_access_token({"sub": user["id"], "username": user["username"], "role": user["role"]})
        return {
            "status": "success",
            "message": "สมัครสมาชิกสำเร็จเรียบร้อยแล้ว",
            "access_token": token,
            "token_type": "bearer",
            "user": user
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการลงทะเบียน: {str(e)}")

@router.post("/login")
async def login_user(payload: Dict[str, Any] = Body(...)):
    """
    Authenticates user and returns JWT bearer token.
    """
    username_or_email = payload.get("username_or_email", "").strip()
    password = payload.get("password", "")

    if not username_or_email or not password:
        raise HTTPException(status_code=400, detail="กรุณากรอกชื่อผู้ใช้/อีเมล และรหัสผ่าน")

    user = db_manager.authenticate_user(username_or_email, password)
    if not user:
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้ หรือรหัสผ่านไม่ถูกต้อง")

    token = create_access_token({
        "sub": user["id"],
        "username": user["username"],
        "role": user["role"],
        "business_id": user.get("business_id")
    })

    return {
        "status": "success",
        "message": f"ยินดีต้อนรับคุณ {user.get('full_name') or user['username']}",
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me")
async def get_current_profile(authorization: Optional[str] = Header(None)):
    """
    Returns current authenticated user details from Authorization header.
    """
    user = get_current_user_from_header(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="เซสชันหมดอายุหรือไม่ถูกต้อง กรุณาเข้าสู่ระบบใหม่")
    return {"status": "success", "user": user}

@router.get("/demo-accounts")
async def get_demo_accounts():
    """
    Returns quick-login demo accounts for presentation & testing convenience.
    """
    return {
        "accounts": [
            {
                "label": "👑 ผู้ดูแลระบบ (System Admin)",
                "username": "admin",
                "password": "admin123",
                "role": "admin",
                "description": "เข้าถึงการตั้งค่าทั้งหมด จัดการโมเดล AI และบัญชีผู้ใช้"
            },
            {
                "label": "🏢 เจ้าของธุรกิจ/ผู้จัดการสาขา (Business Owner)",
                "username": "business_demo",
                "password": "biz123",
                "role": "business_owner",
                "description": "เข้าถึงสถิติเชิงธุรกิจ Footfall, Peak Hours, รายได้และยานพาหนะลูกค้า"
            },
            {
                "label": "👮 เจ้าหน้าที่รักษาความปลอดภัย/เฝ้าระวัง (Security Operator)",
                "username": "guard_operator",
                "password": "guard123",
                "role": "operator",
                "description": "ดูสตรีมสด CCTV แจ้งเตือนเหตุการณ์ผิดปกติ และนับรถ"
            }
        ]
    }
