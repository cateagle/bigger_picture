from fastapi import APIRouter

from src.api.v1.admin.router import router as admin_router
from src.api.v1.annotate.router import router as annotate_router
from src.api.v1.auth.router import router as auth_router
from src.api.v1.dataset.router import router as dataset_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(annotate_router, prefix="/annotate", tags=["annotate"])
router.include_router(dataset_router, prefix="/dataset", tags=["dataset"])
router.include_router(admin_router, prefix="/admin", tags=["admin"])
