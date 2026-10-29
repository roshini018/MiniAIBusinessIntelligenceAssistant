import re
from datetime import date
from app.config import DEFAULT_YEAR

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12, "jan": 1, "feb": 2, "mar": 3,
    "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sept": 9, "sep": 9,
    "oct": 10, "nov": 11, "dec": 12,
}

NAME_RE = re.compile(
    r"\b(" + "|".join(MONTH_NAMES) + r")\b(?:[\s,]*(\d{4}))?",
    re.IGNORECASE,
)
ISO_RE = re.compile(r"\b(\d{4})-(0[1-9]|1[0-2])\b")
YEAR_RE = re.compile(r"\b(20\d\d)\b")

COMPARE_WORDS = re.compile(
    r"\b(compare|comparison|change|changed|difference|versus|vs|between|growth|grew|grow)\b",
    re.IGNORECASE,
)
TREND_WORDS = re.compile(
    r"\b(trend|trends|trending|over time|each month|per month|by month|month by month|monthly)\b",
    re.IGNORECASE,
)
PRODUCT_WORDS = re.compile(
    r"\b(product|products|item|items|merchandise)\b",
    re.IGNORECASE,
)
REGION_WORDS = re.compile(
    r"\b(region|regions|area|areas|territory|territories|zone|zones)\b",
    re.IGNORECASE,
)
SUPERLATIVE_WORDS = re.compile(
    r"\b(top|best|highest|largest|most|leading|maximum|max|greatest)\b",
    re.IGNORECASE,
)
TOTAL_WORDS = re.compile(
    r"\b(total|overall|sum|entire|all|gross|net|cumulative|combined)\b",
    re.IGNORECASE,
)
REVENUE_WORDS = re.compile(
    r"\b(revenue|sales|earnings|income)\b",
    re.IGNORECASE,
)


def extract_months(question: str, default_year: int = DEFAULT_YEAR) -> list[str]:
    """Return distinct months mentioned in the question as 'YYYY-MM', in order of occurrence."""
    # Find all explicit years in the question
    explicit_years = [int(y) for y in YEAR_RE.findall(question)]
    single_explicit_year = explicit_years[-1] if explicit_years else None

    found: list[tuple[int, str]] = []

    # 1. Match ISO formats: 2026-04
    for m in ISO_RE.finditer(question):
        found.append((m.start(), f"{m.group(1)}-{m.group(2)}"))

    # 2. Match Month names
    for m in NAME_RE.finditer(question):
        number = MONTH_NAMES[m.group(1).lower()]
        if m.group(2):
            year = int(m.group(2))
        elif single_explicit_year:
            year = single_explicit_year
        else:
            year = default_year
        found.append((m.start(), f"{year}-{number:02d}"))

    found.sort(key=lambda x: x[0])

    months: list[str] = []
    for _, value in found:
        if value not in months:
            months.append(value)
    return months


def keyword_classify(question: str, default_year: int = DEFAULT_YEAR) -> dict:
    """Rule-based classifier. Returns {'intent': ..., 'params': {...}, 'source': 'keywords'}."""
    q = question.lower().strip()
    effective_year = default_year or date.today().year
    months = extract_months(question, effective_year)

    # 1. Month comparison: requires comparison keywords and at least one month mentioned
    if COMPARE_WORDS.search(q) and (months or re.search(r"\bmonths?\b", q)):
        return {
            "intent": "month_comparison",
            "params": {"months": months},
            "source": "keywords",
        }

    # 2. Monthly trend: explicit trend or month-by-month keywords
    if TREND_WORDS.search(q) and not COMPARE_WORDS.search(q):
        return {"intent": "monthly_trend", "params": {}, "source": "keywords"}

    has_product = bool(PRODUCT_WORDS.search(q))
    has_region = bool(REGION_WORDS.search(q))
    has_superlative = bool(SUPERLATIVE_WORDS.search(q))
    has_revenue = bool(REVENUE_WORDS.search(q))
    has_total = bool(TOTAL_WORDS.search(q))

    # Guard: specific questions about item price, unit cost, or category lookups are unsupported
    if re.search(r"\b(price|cost|category)\b", q) and not (has_superlative and has_revenue):
        return {"intent": "unsupported", "params": {}, "source": "keywords"}

    # 3. Top product: questions targeting best/top/highest product by revenue
    if has_product and (has_superlative or "which" in q or "what product" in q):
        return {"intent": "top_product", "params": {}, "source": "keywords"}

    # 4. Top region: questions targeting best/top/highest region
    if has_region and (has_superlative or "which" in q or "what region" in q):
        return {"intent": "top_region", "params": {}, "source": "keywords"}

    # 5. Total revenue: questions explicitly asking for total/overall/sum of revenue or sales
    # Ambiguous questions like "what is largest revenue" without product or region must NOT be assumed to be total revenue
    if has_total and has_revenue:
        return {"intent": "total_revenue", "params": {}, "source": "keywords"}

    # Explicit phrases asking for total revenue
    if re.search(r"\b(how much|what (is|are) (the|our)?)\s+(total\s+)?(overall\s+)?(revenue|sales)\b", q) and (has_total or "total" in q or "overall" in q or "sum" in q or "all" in q):
        return {"intent": "total_revenue", "params": {}, "source": "keywords"}

    # Fallback to unsupported for ambiguous questions (e.g. "why did sales drop", "weather", "CEO")
    return {"intent": "unsupported", "params": {}, "source": "keywords"}