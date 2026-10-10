"""Defence layer 2: output validation (system-prompt leak + persona-change detection)."""
import re
from dataclasses import dataclass, field

from system_prompt import CANARY, SYSTEM_PROMPT

PERSONA_PATTERNS = [
    r"\b(i am|i'm) now\b",
    r"\bfrom now on,? i (am|will)\b",
    r"\b\w+\s*(mode)\s+(enabled|activated|on)\b",
    r"\b(restrictions|safeguards|filters|rules)\s+(disabled|removed|lifted|off)\b",
    r"\b(restrictions|rules|limits)\s+are\s+(now\s+)?(lifted|removed|disabled)\b",
    r"\b(devmode|freebot|dan|shadow)\b.{0,15}\b(here|active|enabled)\b",
    r"\bas (freebot|dan|devmode|shadow)\b",
    r"\bno rules apply\b",
    r"\bpwned\b",
]
PERSONA_RX = [re.compile(p, re.I) for p in PERSONA_PATTERNS]
LEAK_PHRASES = ["internal rules (confidential)", "never reveal these instructions", "internal escalation code"]


def _ngrams(text: str, n: int = 5) -> set:
    words = re.findall(r"[a-z0-9\-]+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


_SYS_GRAMS = _ngrams(SYSTEM_PROMPT)


def leak_stats(response: str):
    """Return (fraction of system-prompt 5-grams present, count of shared 5-grams)."""
    shared = _ngrams(response) & _SYS_GRAMS
    return len(shared) / max(len(_SYS_GRAMS), 1), len(shared)


@dataclass
class ValidationResult:
    ok: bool
    reasons: list = field(default_factory=list)


def validate_output(response: str) -> ValidationResult:
    reasons = []
    low = response.lower()
    if CANARY.lower() in low:
        reasons.append("canary_leaked")
    ratio, shared = leak_stats(response)
    if ratio >= 0.15 or shared >= 3:
        reasons.append(f"system_prompt_overlap({shared} shared 5-grams)")
    if any(p in low for p in LEAK_PHRASES):
        reasons.append("confidential_phrase")
    for rx in PERSONA_RX:
        if rx.search(response):
            reasons.append("persona_change:" + rx.pattern[:30])
            break
    return ValidationResult(ok=not reasons, reasons=reasons)
