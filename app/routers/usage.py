from fastapi import APIRouter, HTTPException, Query, Response
from app.services.storage import get_storage
import io
import csv
from datetime import datetime

router = APIRouter(prefix="/api/usage", tags=["Usage"])

@router.get("/export")
def export_usage(
    start: float = Query(..., description="Start timestamp (valid float/int timestamp, e.g. 1700000000)"),
    end: float = Query(..., description="End timestamp"),
    granularity: str = Query("hour", regex="^(hour|day)$")
):
    """
    Export usage data as CSV.
    
    Columns: time, token_id, model, request_count, total_tokens, cost
    """
    storage = get_storage()
    
    # 1. Fetch raw logs
    # Note: Usage logs are fetched based on timestamp range [start, end)
    raw_logs = storage.get_usage_logs(start, end)
    
    # 2. Aggregate
    # Format: {(time_bucket, token_id, model): {count, tokens, cost}}
    aggregation = {}
    
    for log in raw_logs:
        ts = log["timestamp"]
        dt = datetime.fromtimestamp(ts)
        
        # Determine time bucket string
        if granularity == "hour":
            # YYYY-MM-DD HH:00:00
            bucket = dt.strftime("%Y-%m-%d %H:00:00")
        else:
            # YYYY-MM-DD
            bucket = dt.strftime("%Y-%m-%d")
            
        key = (bucket, log["key_id"], log["model"])
        
        if key not in aggregation:
            aggregation[key] = {
                "request_count": 0,
                "total_tokens": 0,
                "cost": 0.0
            }
            
        agg = aggregation[key]
        agg["request_count"] += log.get("request_count", 1)
        agg["total_tokens"] += log.get("tokens", 0)
        agg["cost"] += log.get("cost", 0.0)
    
    # 3. Write CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["time", "token_id", "model", "request_count", "total_tokens", "cost"])
    
    # Sort by time, then token, then model
    sorted_keys = sorted(aggregation.keys())
    
    for key in sorted_keys:
        bucket, token_id, model = key
        data = aggregation[key]
        
        writer.writerow([
            bucket,
            token_id,
            model,
            data["request_count"],
            data["total_tokens"],
            # Format cost to avoid scientific notation for small costs
            f"{data['cost']:.6f}"
        ])
        
    return Response(
        content=output.getvalue(), 
        media_type="text/csv", 
        headers={
            "Content-Disposition": f"attachment; filename=usage_export_{granularity}.csv"
        }
    )
