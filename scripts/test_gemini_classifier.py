import logging
from app.llm_classifier import classify_question

logging.basicConfig(level=logging.WARNING)  # shows why a fallback happened

question = input("Ask a business analytics question: ").strip()
if not question:
    print("Please enter a question.")
else:
    print(classify_question(question, 2026))