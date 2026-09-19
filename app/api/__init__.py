from fastapi import APIRouter, Depends

from app.auth import verify_admin
from app.api import injections, keys, logs, rules, upstreams

router = APIRouter(dependencies=[Depends(verify_admin)])
router.include_router(upstreams.router)
router.include_router(keys.router)
router.include_router(logs.router)
router.include_router(rules.router)
router.include_router(injections.router)
