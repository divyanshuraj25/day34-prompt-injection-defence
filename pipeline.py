"""The assistant: optional 3 defence layers around a Gemini call."""
import config
from llm_client import call_llm
from moderation import moderate_text
from output_validator import validate_output
from sanitizer import sanitize_chunk, sanitize_query
from system_prompt import SYSTEM_PROMPT


def _result(status, response, layer=None, details=None):
    return {"status": status, "response": response, "layer": layer, "details": details or []}


def chat(message, context_chunks=None, *, sanitize=True, moderate=True, validate=True):
    chunks = list(context_chunks or [])
    notes = []

    # ---- Layer 1: input sanitisation -------------------------------------
    if sanitize:
        q = sanitize_query(message)
        if q.flagged:
            return _result("blocked_by_sanitizer", config.REJECT_MESSAGE, "sanitizer", q.matches)
        message = q.cleaned
        cleaned = []
        for c in chunks:
            r = sanitize_chunk(c)
            if r.flagged:
                notes.append(f"chunk sanitised: {r.matches}")
            if r.cleaned:
                cleaned.append(r.cleaned)
        chunks = cleaned

    # ---- Layer 3: moderation (pre-call) ----------------------------------
    if moderate:
        m = moderate_text(message)
        if m.flagged:
            return _result("blocked_by_moderation", config.REJECT_MESSAGE, "moderation", [m.reason])

    # ---- Build prompt ----------------------------------------------------
    if chunks and sanitize:   # protected: fence documents as untrusted data
        docs = "\n".join(f"<untrusted_document>\n{c}\n</untrusted_document>" for c in chunks)
    else:                     # naive baseline: paste chunks straight in
        docs = "\n\n".join(chunks)
    prompt = (f"Document context:\n{docs}\n\n" if docs else "") + f"User question: {message}"

    response = call_llm(SYSTEM_PROMPT, prompt)

    # ---- Layer 2: output validation --------------------------------------
    if validate:
        v = validate_output(response)
        if not v.ok:
            return _result("blocked_by_output_validator", config.REJECT_MESSAGE, "output_validator", v.reasons)

    return _result("answered", response, None, notes)
