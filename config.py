import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # dotenv optional
    pass

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MOCK_LLM = os.getenv("MOCK_LLM", "0") == "1"
MODERATION_THRESHOLD = float(os.getenv("MODERATION_THRESHOLD", "0.5"))
MODERATION_FAIL_CLOSED = os.getenv("MODERATION_FAIL_CLOSED", "1") == "1"
CALL_DELAY_SECONDS = float(os.getenv("CALL_DELAY_SECONDS", "1.0"))

REJECT_MESSAGE = "Sorry, I can't process that request."
