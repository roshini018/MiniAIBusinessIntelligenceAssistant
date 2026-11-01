import sqlite3
from app import queries
from app.config import DEFAULT_DB_PATH, DEFAULT_YEAR
from app.llm_classifier import classify_question
from app.queries import AppError

MAX_QUESTION_LENGTH = 500
SUPPORTED = [
    "total revenue",
    "top product by revenue",
    "monthly revenue trend",
    "top region by revenue",
    "revenue comparison between two months",
]
UNSUPPORTED_MESSAGE = (
    "I can't answer that question. Supported questions include: "
    "Total revenue, Top product by revenue, Top region by revenue, "
    "Monthly revenue trend, and Revenue comparison between two months. "
    "You can also ask about specific products, regions, months, rankings, "
    "or highest and lowest performers."
)

def answer_question(
    question: str,
    db_path: str | None = None,
    classifier=classify_question,
) -> dict:
    question = (question or "").strip()
    if not question:
        raise AppError("Question cannot be empty.", 400)
    if len(question) > MAX_QUESTION_LENGTH:
        raise AppError(
            f"Question is too long (max {MAX_QUESTION_LENGTH} characters).", 400
        )

    target_db = db_path if db_path is not None else queries.DEFAULT_DB_PATH
    conn = queries.get_conn(target_db)

    try:
        default_year = _latest_year(conn)
        decision = classifier(question, default_year)
        intent = decision["intent"]

        if intent == "total_revenue":
            result = queries.total_revenue(conn)
        elif intent == "top_product":
            target = decision.get("params", {}).get("target")
            product = decision.get("params", {}).get("product")
            if target == "specific":
                product = queries.find_product(conn, question) or (queries.find_product(conn, product) if product else None) or product
            result = queries.top_product(conn, target=target, product_name=product)
        elif intent == "monthly_trend":
            target = decision.get("params", {}).get("target")
            months = decision.get("params", {}).get("months", [])
            month = decision.get("params", {}).get("month") or (months[0] if (target == "specific" and months) else None)
            result = queries.monthly_trend(conn, target=target, month=month)
        elif intent == "top_region":
            target = decision.get("params", {}).get("target")
            region = decision.get("params", {}).get("region")
            if target == "specific":
                region = queries.find_region(conn, question) or (queries.find_region(conn, region) if region else None) or region
            result = queries.top_region(conn, target=target, region_name=region)
        elif intent == "month_comparison":
            months = decision.get("params", {}).get("months", [])
            if len(months) != 2:
                raise AppError(
                    "Please name exactly two months to compare, "
                    "e.g. 'Compare revenue between January and February'.",
                    400,
                )
            if months[0] == months[1]:
                raise AppError("Please name two distinct months to compare.", 400)
            result = queries.month_comparison(conn, months[0], months[1])
        elif intent == "ambiguous":
            msg = decision.get("params", {}).get("message") or (
                "Please clarify whether you would like to see the highest/lowest performance by month, product, or region."
            )
            raise AppError(msg, 400)
        else:
            raise AppError(UNSUPPORTED_MESSAGE, 422)
    except AppError:
        raise
    except sqlite3.Error:
        raise AppError("A database error occurred.", 500)
    finally:
        conn.close()

    return {
        "question": question,
        "intent": result["intent"],
        "answer": result["answer"],
        "sql_used": result["sql"],
        "params": result["params"],
        "supporting_data": result["data"],
        "classified_by": decision.get("source", "unknown"),
    }


def _latest_year(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute(
            "SELECT MAX(substr(month, 1, 4)) FROM sales WHERE counted = 1"
        ).fetchone()
        return int(row[0]) if row and row[0] else DEFAULT_YEAR
    except Exception:
        return DEFAULT_YEAR