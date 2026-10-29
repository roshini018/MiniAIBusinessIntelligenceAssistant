import logging
import sqlite3
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import queries
from app.queries import AppError
from app.service import answer_question

logger = logging.getLogger("bi-assistant")
app = FastAPI(title="Mini AI BI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

MONTH_ABBRS = {
    "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
    "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
}


def _format_timeframe(start: str | None, end: str | None) -> str:
    if not start or not end:
        return ""
    try:
        start_y, start_m = start.split("-")
        end_y, end_m = end.split("-")
        s_abbr = MONTH_ABBRS.get(start_m, start_m)
        e_abbr = MONTH_ABBRS.get(end_m, end_m)
        if start_y == end_y:
            return f"{s_abbr} – {e_abbr} {start_y}"
        return f"{s_abbr} {start_y} – {e_abbr} {end_y}"
    except Exception:
        return f"{start} – {end}"


class AskRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(body: AskRequest):
    return answer_question(body.question)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/kpis")
def kpis():
    conn = queries.get_conn()
    try:
        rev_res = queries.total_revenue(conn)
        prod_res = queries.top_product(conn)
        reg_res = queries.top_region(conn)
        trend_res = queries.monthly_trend(conn)

        rev_data = rev_res["data"][0] if rev_res["data"] else {}
        top_prod = prod_res["data"][0] if prod_res["data"] else {}
        top_reg = reg_res["data"][0] if reg_res["data"] else {}

        trend_data = trend_res.get("data", [])
        start_month = trend_data[0]["month"] if trend_data else None
        end_month = trend_data[-1]["month"] if trend_data else None
        timeframe_label = _format_timeframe(start_month, end_month)

        return {
            "total_revenue": rev_data.get("total_revenue", 0),
            "orders_counted": rev_data.get("orders_counted", 0),
            "top_product": {
                "name": top_prod.get("product"),
                "revenue": top_prod.get("revenue", 0),
            },
            "top_region": {
                "name": top_reg.get("region"),
                "revenue": top_reg.get("revenue", 0),
            },
            "timeframe": {
                "start_month": start_month,
                "end_month": end_month,
                "label": timeframe_label,
            },
        }
    except AppError:
        raise
    except sqlite3.Error:
        raise AppError("A database error occurred.", 500)
    finally:
        conn.close()


@app.get("/chart-data")
def chart_data():
    """Return aggregated data for overview charts: monthly trend, product and region breakdowns."""
    conn = queries.get_conn()
    try:
        trend_res = queries.monthly_trend(conn)
        prod_res = queries.top_product(conn)
        reg_res = queries.top_region(conn)
        return {
            "monthly_trend": trend_res.get("data", []),
            "products": prod_res.get("data", []),
            "regions": reg_res.get("data", []),
        }
    except AppError:
        raise
    except sqlite3.Error:
        raise AppError("A database error occurred.", 500)
    finally:
        conn.close()


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status, content={"error": exc.message})


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception):
    logger.exception("Unexpected error")
    return JSONResponse(
        status_code=500,
        content={"error": "Something went wrong on our side."},
    )