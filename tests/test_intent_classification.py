import pytest
from app.intent import keyword_classify, extract_months


# 1. Synonyms and alternate phrasings for every supported intent
@pytest.mark.parametrize(
    "question,expected_intent,expected_target",
    [
        # Total revenue
        ("What is our total revenue?", "total_revenue", None),
        ("How much revenue did we generate?", "total_revenue", None),
        ("What are our total sales?", "total_revenue", None),
        ("How much did we earn?", "total_revenue", None),
        ("What is the overall revenue?", "total_revenue", None),
        ("Show me the total sales amount.", "total_revenue", None),
        ("How much did we sell?", "total_revenue", None),
        ("What was our gross sales amount?", "total_revenue", None),
        ("Tell me our combined revenue.", "total_revenue", None),
        ("What is our cumulative revenue?", "total_revenue", None),
        ("How much revenue was generated overall?", "total_revenue", None),
        
        # Highest / lowest generic revenue (maps to monthly_trend)
        ("What is the highest revenue?", "monthly_trend", "highest"),
        ("What is the lowest revenue?", "monthly_trend", "lowest"),
        ("What was the maximum revenue?", "monthly_trend", "highest"),
        ("What was the minimum revenue earned?", "monthly_trend", "lowest"),

        # Monthly extremes & trends
        ("Which month had the highest revenue?", "monthly_trend", "highest"),
        ("Which month generated the most sales?", "monthly_trend", "highest"),
        ("What was our best-performing month?", "monthly_trend", "highest"),
        ("Which month had the lowest revenue?", "monthly_trend", "lowest"),
        ("What was our worst-performing month?", "monthly_trend", "lowest"),
        ("Which month had the lowest sales?", "monthly_trend", "lowest"),
        ("Show monthly revenue trends.", "monthly_trend", "trend"),
        ("How are sales changing month by month?", "monthly_trend", "trend"),
        ("Revenue per month over time", "monthly_trend", "trend"),
        ("Is revenue increasing or decreasing?", "monthly_trend", "trajectory"),
        ("Is revenue growing or declining?", "monthly_trend", "trajectory"),
        ("Is sales going up or down?", "monthly_trend", "trajectory"),

        # Product performance
        ("Which product earned the most revenue?", "top_product", "highest"),
        ("Which product generated the highest sales?", "top_product", "highest"),
        ("What is our best-selling product by revenue?", "top_product", "highest"),
        ("Show the top product.", "top_product", "highest"),
        ("Which product contributes the most to sales?", "top_product", "highest"),
        ("Which product generated the least revenue?", "top_product", "lowest"),
        ("Which item earned the lowest revenue?", "top_product", "lowest"),
        ("Rank products by revenue.", "top_product", "ranking"),
        ("Show revenue breakdown by product.", "top_product", "ranking"),
        ("List all products by revenue.", "top_product", "ranking"),

        # Regional performance
        ("Which region has the highest sales?", "top_region", "highest"),
        ("Which region generated the most revenue?", "top_region", "highest"),
        ("Which region performed best?", "top_region", "highest"),
        ("Which region generated the lowest sales?", "top_region", "lowest"),
        ("Show revenue by region.", "top_region", "ranking"),
        ("Rank regions by revenue.", "top_region", "ranking"),
        ("Regional revenue breakdown.", "top_region", "ranking"),
    ],
)
def test_intent_classification_synonyms(question, expected_intent, expected_target):
    res = keyword_classify(question)
    assert res["intent"] == expected_intent
    if expected_target is not None:
        assert res["params"].get("target") == expected_target


# 2. Case differences, punctuation, whitespace, and contractions
@pytest.mark.parametrize(
    "noisy_question,expected_intent",
    [
        ("   what's our total revenue?   ", "total_revenue"),
        ("WHAT IS OUR TOTAL REVENUE?!?", "total_revenue"),
        ("how    much    did    we    earn   ????", "total_revenue"),
        ("wHaT aRe OuR tOtAl SaLeS?", "total_revenue"),
        ("what's the top product by revenue?!", "top_product"),
        ("   RANK   PRODUCTS   BY   REVENUE...   ", "top_product"),
        ("WHICH REGION HAD HIGHEST SALES???", "top_region"),
        ("compare  january   and   february  2026...", "month_comparison"),
        ("what was the revenue in april???", "monthly_trend"),
    ],
)
def test_case_punctuation_whitespace_contractions(noisy_question, expected_intent):
    res = keyword_classify(noisy_question)
    assert res["intent"] == expected_intent


# 3. Month extraction and comparison syntax
def test_month_extraction_formats():
    assert extract_months("Revenue in 2026-05 and 2026-06") == ["2026-05", "2026-06"]
    assert extract_months("Compare April and May 2026") == ["2026-04", "2026-05"]
    assert extract_months("From December 2025 to January 2026") == ["2025-12", "2026-01"]
    assert extract_months("What was revenue in February?") == ["2026-02"]
    assert extract_months("Invalid month Octember or Foobar") == []
    # Deduplication preserving order
    assert extract_months("January 2026 and January 2026") == ["2026-01"]


@pytest.mark.parametrize(
    "question,expected_months",
    [
        ("Compare April and May 2026.", ["2026-04", "2026-05"]),
        ("How much did revenue increase from April to May?", ["2026-04", "2026-05"]),
        ("What is the percentage change between April and May?", ["2026-04", "2026-05"]),
        ("Compare January with May.", ["2026-01", "2026-05"]),
        ("Which month had higher revenue, April or May?", ["2026-04", "2026-05"]),
        ("Did revenue grow from April to May?", ["2026-04", "2026-05"]),
        ("Did sales drop between March 2026 and April 2026?", ["2026-03", "2026-04"]),
        ("Difference between Jan and Feb 2026", ["2026-01", "2026-02"]),
        ("Revenue comparison: Jan versus Feb", ["2026-01", "2026-02"]),
    ],
)
def test_month_comparison_phrasing_variations(question, expected_months):
    res = keyword_classify(question)
    assert res["intent"] == "month_comparison"
    assert res["params"]["months"] == expected_months


# 4. Ambiguous wording must request concise clarification
@pytest.mark.parametrize(
    "ambiguous_question,expected_keyword",
    [
        ("Which performed best?", "month, product, or region"),
        ("What was the highest?", "month, product, or region"),
        ("Which is the lowest?", "month, product, or region"),
        ("Show rankings", "month, product, or region"),
        ("Compare sales", "two months"),
        ("Compare revenue", "two months"),
        ("Compare", "two months"),
    ],
)
def test_ambiguous_questions_require_clarification(ambiguous_question, expected_keyword):
    res = keyword_classify(ambiguous_question)
    assert res["intent"] == "ambiguous"
    assert expected_keyword in res["params"]["message"].lower()


# 5. Truly unsupported questions must return unsupported
@pytest.mark.parametrize(
    "unsupported_question",
    [
        # Item price lookup
        "What is the price of the Monitor?",
        "What does the Laptop Stand cost?",
        "Unit price of Keyboard",
        "Price per unit of Mouse",
        # Category lookup
        "Which category does the Wireless Mouse belong to?",
        "What category is the Office Chair?",
        # Reason / Why questions
        "Why did sales drop last week?",
        "Why is Laptop our top product?",
        # Personnel / Management
        "Who is the CEO?",
        "Who is our sales manager?",
        "List all company employees",
        "What is the salary of staff?",
        # External domain
        "What is the weather today?",
        "Is it going to rain tomorrow?",
        "What is the stock price of Apple?",
        # Injection and data mutation attempts
        "DROP TABLE sales;",
        "DELETE FROM sales WHERE region = 'North'",
        "INSERT INTO sales (transaction_id) VALUES ('X999')",
        "UPDATE sales SET revenue = 1000000",
    ],
)
def test_truly_unsupported_questions(unsupported_question):
    res = keyword_classify(unsupported_question)
    assert res["intent"] == "unsupported"


# 6. Conflicting phrases: ensure classifier chooses the correct specific entity
@pytest.mark.parametrize(
    "question,expected_intent,expected_target",
    [
        # Mentions "total revenue" AND "top product": should focus on top_product
        ("What is the total revenue of the top product?", "top_product", "highest"),
        # Mentions "total revenue" AND "top region": should focus on top_region
        ("What is the total revenue of the top region?", "top_region", "highest"),
        # Mentions "total revenue" AND a specific month: should focus on that specific month
        ("What was the total revenue in May 2026?", "monthly_trend", "specific"),
        # Mentions "highest" AND a specific product: should ask for product revenue
        ("How much revenue did the Monitor generate?", "top_product", "specific"),
        # Mentions "revenue" AND a specific region: should ask for region revenue
        ("How much revenue came from the South region?", "top_region", "specific"),
        # Mentions item price of top product: must be unsupported
        ("What is the unit price of the top product?", "unsupported", None),
    ],
)
def test_conflicting_phrase_resolution(question, expected_intent, expected_target):
    res = keyword_classify(question)
    assert res["intent"] == expected_intent
    if expected_target is not None:
        assert res["params"].get("target") == expected_target
