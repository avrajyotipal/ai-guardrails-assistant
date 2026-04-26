from fastapi import APIRouter, Query
from typing import Optional
from guardrails.monitoring_layer import MonitoringLayerGuardrail

router = APIRouter()
_monitor = MonitoringLayerGuardrail()


@router.get("/monitoring/logs")
def get_logs(
    session_id: Optional[str] = Query(None),
    blocked_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    logs = _monitor.get_logs(
        session_id=session_id,
        blocked_only=blocked_only,
        limit=limit,
        offset=offset,
    )
    return {"count": len(logs), "logs": logs}


@router.get("/monitoring/stats")
def get_stats():
    return _monitor.get_stats()
