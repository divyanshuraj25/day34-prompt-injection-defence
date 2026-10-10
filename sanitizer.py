"""Defence layer 1: input sanitisation (user queries + retrieved document chunks)."""
import re
import unicodedata
from dataclasses import dataclass, field

ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad"), None)

PATTERNS = [
    (r"(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+|your\s+)?(previous|prior|above|earlier|preceding|former)?\s*(instructions|prompts?|rules|messages|guidelines)", "ignore_previous"),
    (r"your\s+(system\s+)?prompt\s+(is|says|was|reads)", "your_system_prompt_is"),
    (r"(reveal|show|print|display|repeat|output|leak|tell me|share|recit\w*|read\w*|write out)\b.{0,50}\b(system prompt|system message|initial instructions|hidden instructions|your instructions|internal instructions|internal (codes?|rules|passphrase)|passphrase|access code|configuration)", "prompt_leak_request"),
    (r"(everything|all\s+(of\s+)?(the\s+)?text|the\s+text)\s+(above|before)\b", "repeat_above"),
    (r"(repeat|translate|copy|summari[sz]e)\b.{0,30}\b(everything|all)\b.{0,15}\b(above|before)\b", "repeat_above"),
    (r"\byou\s+are\s+now\b", "role_override"),
    (r"\b(from now on|henceforth),?\s+you\s+(are|will|must|shall)", "role_override"),
    (r"\bact\s+as\s+(if\s+you\s+(are|were)\s+)?(an?\s+)?(unrestricted|unfiltered|jailbroken|different|evil)", "role_override"),
    (r"\b(developer|dev|debug|god|admin|sudo|dan)\s+mode\b", "privileged_mode"),
    (r"\[\s*(system|admin|developer|root)[^\]]*\]", "fake_system_tag"),
    (r"\b(system|admin|developer)\s+override\b", "fake_system_tag"),
    (r"(disable|bypass|remove|turn off|lift)\b.{0,30}\b(restrictions|safety|filters|guardrails|rules|limits)", "disable_safeguards"),
    (r"\b(no|without any|free of)\s+(rules|restrictions|limits|filters)\b", "no_rules"),
    (r"\bstay\s+in\s+character\b", "persona_lock"),
    (r"\bnote\s+(to|for)\s+(the\s+)?(ai|assistant|model|llm|chatbot)\b", "note_to_assistant"),
    (r"(word\s+for\s+word|verbatim).{0,60}(instructions|prompt|rules|codes?)|(instructions|prompt|rules).{0,40}(word\s+for\s+word|verbatim)", "verbatim_instructions"),
    (r"(pretend|imagine|role-?play|play a game|write a (story|play|poem|script)).{0,100}(no rules|no restrictions|reads? aloud|its (initial |system )?(instructions|prompt)|secret|passphrase|internal)", "fiction_framing"),
]
COMPILED = [(re.compile(p, re.I | re.S), name) for p, name in PATTERNS]


@dataclass
class SanitizeResult:
    flagged: bool
    matches: list = field(default_factory=list)
    cleaned: str = ""


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(ZERO_WIDTH)
    return re.sub(r"\s+", " ", text).strip()


def scan(text: str) -> list:
    norm = normalize(text)
    return sorted({name for rx, name in COMPILED if rx.search(norm)})


def sanitize_query(query: str) -> SanitizeResult:
    """User queries: REJECT on any match."""
    matches = scan(query)
    return SanitizeResult(flagged=bool(matches), matches=matches, cleaned=normalize(query))


def sanitize_chunk(chunk: str) -> SanitizeResult:
    """Retrieved document chunks: STRIP hidden markup and any injected lines, keep the rest."""
    text = re.sub(r"<!--.*?-->", " ", chunk, flags=re.S)           # HTML comments
    text = unicodedata.normalize("NFKC", text).translate(ZERO_WIDTH)
    matches, kept = set(), []
    # split into sentences/lines so one bad sentence doesn't kill the whole chunk
    for piece in re.split(r"(?<=[.!?])\s+|\n+", text):
        hit = scan(piece)
        if hit:
            matches.update(hit)
        elif piece.strip():
            kept.append(piece.strip())
    # the raw (pre-strip) chunk may have had a comment-hidden attack; scan it too
    matches.update(scan(chunk))
    return SanitizeResult(flagged=bool(matches), matches=sorted(matches), cleaned=" ".join(kept))
