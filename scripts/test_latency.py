import time
from app.llm_classifier import _classify_with_gemini

start = time.time()
print(_classify_with_gemini("what is largest revenue", 2026))
print(f"{time.time() - start:.1f}s") 