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
    "I can't answer that question. I am designed to assist with these 5 specific business intelligence metrics:\n"
    "1. Total revenue (e.g., 'What is our total revenue?')\n"
    "2. Top product by revenue (e.g., 'Which product earned the most revenue?')\n"
    "3. Monthly revenue trend (e.g., 'Show monthly revenue trends')\n"
    "4. Top region by revenue (e.g., 'Which region had the highest sales?')\n"
    "5. Revenue comparison between two months (e.g., 'Compare revenue between April and May 2026')\n\n"
    "Please try rephrasing your question using one of these supported question types."
)


def answer_question(
    question: str,
    db_path: str = DEFAULT_DB_PATH,
    classifier=classify_question,
) -> dict:
    question = (question or "").strip()
    if not question:
        raise AppError("Question cannot be empty.", 400)
    if len(question) > MAX_QUESTION_LENGTH:
        raise AppError(
            f"Question is too long (max {MAX_QUESTION_LENGTH} characters).", 400
        )

    conn = queries.get_conn(db_path)

    try:
        default_year = _latest_year(conn)
        decision = classifier(question, default_year)
        intent = decision["intent"]

        if intent == "total_revenue":
            result = queries.total_revenue(conn)
        elif intent == "top_product":
            result = queries.top_product(conn)
        elif intent == "monthly_trend":
            result = queries.monthly_trend(conn)
        elif intent == "top_region":
            result = queries.top_region(conn)
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