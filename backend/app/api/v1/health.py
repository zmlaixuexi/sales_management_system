from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"success": True, "data": {"status": "ok"}, "message": "服务正常"}


@router.get("/version")
def version():
    return {"success": True, "data": {"version": "0.1.0"}, "message": "查询成功"}
