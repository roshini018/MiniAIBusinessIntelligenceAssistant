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
    r"\b(compare|comparison|change|changed|difference|versus|vs|between|growth|grew|grow|increase|increased|decrease|decreased|drop|dropped|rise|rose)\b",
    re.IGNORECASE,
)
TREND_WORDS = re.compile(
    r"\b(trend|trends|trending|over time|each month|per month|by month|month by month|monthly)\b",
    re.IGNORECASE,
)
PRODUCT_WORDS = re.compile(
    r"\b(product|products|item|items|merchandise|selling)\b",
    re.IGNORECASE,
)
REGION_WORDS = re.compile(
    r"\b(region|regions|regional|area|areas|territory|territories|zone|zones)\b",
    re.IGNORECASE,
)
REGION_NAMES = re.compile(
    r"\b(north|south|east|west|central|northeast|northwest|southeast|southwest)\b",
    re.IGNORECASE,
)
SUPERLATIVE_WORDS = re.compile(
    r"\b(top|best|highest|largest|most|leading|maximum|max|greatest)\b",
    re.IGNORECASE,
)
LOWEST_WORDS = re.compile(
    r"\b(lowest|worst|least|bottom|minimum|min|smallest)\b",
    re.IGNORECASE,
)
RANK_WORDS = re.compile(
    r"\b(rank|ranking|rankings|breakdown|by product|by region|by month|each product|each region|all products|all regions|list)\b",
    re.IGNORECASE,
)
TRAJECTORY_WORDS = re.compile(
    r"\b(increasing or decreasing|growing or declining|up or down|trajectory|going up|going down)\b",
    re.IGNORECASE,
)
TOTAL_WORDS = re.compile(
    r"\b(total|overall|sum|entire|all|gross|combined|cumulative|amount)\b",
    re.IGNORECASE,
)
REVENUE_WORDS = re.compile(
    r"\b(revenue|sales?|earnings?|income|turnover)\b",
    re.IGNORECASE,
)
EARN_WORDS = re.compile(
    r"\b(earn|earned|earning|earnings|generate|generated|made|make|sell|sold)\b",
    re.IGNORECASE,
)


def extract_months(question: str, default_year: int = DEFAULT_YEAR) -> list[str]:
    """Return distinct months mentioned in the question as 'YYYY-MM', in order of occurrence."""
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

    # 0. Unsupported guards: questions out of scope must be rejected cleanly
    # Non-sales instructions, SQL injections, weather, employee/person questions, reason/why questions
    if re.search(r"\b(drop table|delete from|update sales|insert into|alter table)\b", q):
        return {"intent": "unsupported", "params": {}, "source": "keywords"}
    if re.search(r"\b(weather|temperature|forecast|rain|cloudy)\b", q):
        return {"intent": "unsupported", "params": {}, "source": "keywords"}
    if re.search(r"\b(ceo|founder|manager|employee|employees|staff|salary|who is|who are)\b", q):
        return {"intent": "unsupported", "params": {}, "source": "keywords"}
    if re.search(r"^\s*why\b", q):
        return {"intent": "unsupported", "params": {}, "source": "keywords"}

    has_product = bool(PRODUCT_WORDS.search(q))
    has_region = bool(REGION_WORDS.search(q)) or bool(REGION_NAMES.search(q))
    has_superlative = bool(SUPERLATIVE_WORDS.search(q))
    has_lowest = bool(LOWEST_WORDS.search(q))
    has_revenue = bool(REVENUE_WORDS.search(q)) or bool(EARN_WORDS.search(q))
    has_total = bool(TOTAL_WORDS.search(q))
    has_ranking = bool(RANK_WORDS.search(q))
    has_trajectory = bool(TRAJECTORY_WORDS.search(q))
    has_compare = bool(COMPARE_WORDS.search(q))
    has_month_word = bool(re.search(r"\bmonths?\b", q))

    # Guard: specific questions about item price, unit cost, or category lookups are unsupported
    if re.search(r"\b(price|unit cost|cost per unit)\b", q) and not (has_superlative and has_revenue):
        return {"intent": "unsupported", "params": {}, "source": "keywords"}
    if re.search(r"\b(category|categories)\b", q) and not (has_superlative and has_revenue):
        return {"intent": "unsupported", "params": {}, "source": "keywords"}

    # 1. Month comparison
    # Either 2 months mentioned with comparison/difference/growth/increase/versus, or 'higher'/'lower'/'or'
    if len(months) == 2:
        is_comparison = (
            has_compare
            or bool(re.search(r"\b(or|versus|vs|between|higher|lower|more|less|better|grow|increase)\b", q))
        )
        if is_comparison:
            return {
                "intent": "month_comparison",
                "params": {"months": months},
                "source": "keywords",
            }

    # Month comparison with only 1 month explicitly asked to compare: returns month_comparison so service can ask for 2 months
    if has_compare and (len(months) == 1 or has_month_word) and not (has_product or has_region):
        if not re.search(r"\b(compare\s+(products?|regions?))\b", q):
            return {
                "intent": "month_comparison",
                "params": {"months": months},
                "source": "keywords",
            }

    # Ambiguous comparison without any entity or months: "compare", "compare sales", "compare revenue"
    if has_compare and not (months or has_product or has_region or has_month_word):
        return {
            "intent": "ambiguous",
            "params": {
                "message": "Please specify which two months you would like to compare (e.g., 'Compare April and May 2026')."
            },
            "source": "keywords",
        }

    # 2. Specific single-month lookup (e.g., "Show revenue for May 2026", "What was the revenue in April?")
    if len(months) == 1 and not (has_product or has_region or has_superlative or has_lowest or has_compare):
        return {
            "intent": "monthly_trend",
            "params": {"months": months, "month": months[0], "target": "specific"},
            "source": "keywords",
        }

    # 3. Monthly trend / trajectory / month-by-month
    if has_trajectory:
        return {
            "intent": "monthly_trend",
            "params": {"target": "trajectory"},
            "source": "keywords",
        }

    if TREND_WORDS.search(q) and not (has_product or has_region):
        return {
            "intent": "monthly_trend",
            "params": {"target": "trend"},
            "source": "keywords",
        }

    # 4. Regional questions
    # Specific region lookup (e.g., "How much revenue came from the South region?")
    reg_match = REGION_NAMES.search(q)
    if reg_match and not (has_superlative or has_lowest or has_ranking or "which" in q):
        matched_reg = reg_match.group(1).title()
        return {
            "intent": "top_region",
            "params": {"region": matched_reg, "target": "specific"},
            "source": "keywords",
        }

    if has_region:
        if has_lowest:
            return {"intent": "top_region", "params": {"target": "lowest"}, "source": "keywords"}
        if has_ranking or re.search(r"\b(by region|revenue by region|each region|show revenue by region)\b", q):
            return {"intent": "top_region", "params": {"target": "ranking"}, "source": "keywords"}
        if has_superlative or "which" in q or "best" in q or "highest" in q:
            return {"intent": "top_region", "params": {"target": "highest"}, "source": "keywords"}

    # 5. Product questions
    # Check for specific product lookup pattern: "How much revenue did [the] [Product] generate/make?" or "came from [Product]"
    prod_lookup_match = re.search(
        r"\b(?:how\s+much\s+revenue\s+(?:did|came\s+from)|revenue\s+(?:for|of|from)|how\s+much\s+did)\s+(?:the\s+)?(.+?)(?:\s+(?:generate|make|earn|bring|produce|come\s+from)|\?|$)",
        question,
        re.IGNORECASE,
    )
    is_we_query = bool(re.search(r"\bhow\s+much\s+did\s+we\b", q))
    if not months and not is_we_query and prod_lookup_match:
        extracted = prod_lookup_match.group(1).strip()
        extracted_words = extracted.lower().split()
        generic_product_exclusions = {
            "we", "our store", "the company", "our company", "the business",
            "all", "total", "overall", "each", "product", "item"
        }
        is_superlative = any(w in extracted_words for w in ["top", "best", "lowest", "worst", "highest", "leading", "least", "most"])
        if extracted.lower() not in generic_product_exclusions and not is_superlative and "we" not in extracted_words:
            return {
                "intent": "top_product",
                "params": {"product": extracted, "target": "specific"},
                "source": "keywords",
            }

    if has_product:
        if has_lowest:
            return {"intent": "top_product", "params": {"target": "lowest"}, "source": "keywords"}
        if has_ranking or re.search(r"\b(by product|rank products|ranking)\b", q):
            return {"intent": "top_product", "params": {"target": "ranking"}, "source": "keywords"}
        if (
            has_superlative
            or "which" in q
            or "what product" in q
            or "top product" in q
            or "contribute" in q
            or "contributes" in q
        ):
            return {"intent": "top_product", "params": {"target": "highest"}, "source": "keywords"}

    # 6. Highest / Lowest Month questions
    if has_month_word and (has_superlative or has_lowest or "best" in q or "worst" in q):
        target = "lowest" if has_lowest or "worst" in q else "highest"
        return {
            "intent": "monthly_trend",
            "params": {"target": target},
            "source": "keywords",
        }

    # 7. Generic Highest / Lowest revenue without product or region
    # Requirement: "Interpret generic 'highest revenue' or 'lowest revenue' using monthly revenue when no product or region is specified."
    if (has_superlative or has_lowest or "best" in q or "worst" in q) and has_revenue:
        target = "lowest" if has_lowest or "worst" in q else "highest"
        return {
            "intent": "monthly_trend",
            "params": {"target": target},
            "source": "keywords",
        }

    # 8. Genuinely ambiguous performance questions without dimension or revenue
    # E.g. "Which performed best?", "What is the highest?", "Which is the lowest?", "Show rankings"
    if (has_superlative or has_lowest or has_ranking or "best" in q or "worst" in q) and not (has_revenue or has_product or has_region or has_month_word):
        return {
            "intent": "ambiguous",
            "params": {
                "message": "Please clarify whether you would like to see the highest/lowest performance by month, product, or region."
            },
            "source": "keywords",
        }

    # 9. Total / Overall revenue questions
    # E.g., "What is our total revenue?", "How much revenue did we generate?", "What are our total sales?", "How much did we earn?", "Show me the total sales amount."
    if has_revenue:
        if has_total:
            return {"intent": "total_revenue", "params": {}, "source": "keywords"}
        if re.search(r"\b(how\s+much\s+(?:revenue|sales|did\s+we\s+(?:earn|make|sell))|what\s+(?:is|are|was|were)\s*(?:our|the)?\s*(?:total|overall)?\s*(?:revenue|sales))\b", q):
            return {"intent": "total_revenue", "params": {}, "source": "keywords"}
        if re.search(r"\bhow\s+much\s+(?:did\s+we\s+(?:earn|make|sell)|was\s+earned|was\s+made|was\s+sold)\b", q):
            return {"intent": "total_revenue", "params": {}, "source": "keywords"}
        if re.search(r"\bhow\s+much\s+(?:revenue|sales)\s+(?:did\s+we\s+generate|was\s+generated)\b", q):
            return {"intent": "total_revenue", "params": {}, "source": "keywords"}

    # Fallback to unsupported for out of scope or unknown questions
    return {"intent": "unsupported", "params": {}, "source": "keywords"}