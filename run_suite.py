"""Run all 10 attacks BEFORE (no defences) and AFTER (3 layers), print raw responses, save a table.

    python run_suite.py            # real Gemini
    MOCK_LLM=1 python run_suite.py # offline simulation (pipeline check only)
"""
import json
import pathlib
import sys

import config
from attacks import ATTACKS, BENIGN_QUERIES, EXTRA_ATTACKS, MODERATION_PROBES
from classifier import classify
from moderation import moderate_text
from pipeline import chat

OUT = pathlib.Path(__file__).parent / "results"
OUT.mkdir(exist_ok=True)
LINE = "=" * 78


def run(label, protected, attacks):
    print(f"\n{LINE}\n  {label}\n{LINE}")
    rows = []
    for a in attacks:
        res = chat(a["user_query"], a.get("context_chunks"),
                   sanitize=protected, moderate=protected, validate=protected)
        verdict = classify(a, res)
        print(f"\n[{a['id']:>2}] {a['category']} | {a['name']}")
        print(f"     payload : {a['user_query']}")
        if a.get("context_chunks"):
            print(f"     chunks  : {a['context_chunks']}")
        print(f"     status  : {res['status']} {res['details'] or ''}")
        print(f"     RAW RESPONSE:\n{res['response']}")
        print(f"     VERDICT : {verdict}")
        rows.append({"id": a["id"], "category": a["category"], "name": a["name"], "status": res["status"],
                     "layer": res["layer"], "details": res["details"], "response": res["response"], "verdict": verdict})
    return rows


def count(rows, v):
    return sum(r["verdict"] == v for r in rows)


def main():
    if not config.MOCK_LLM and not config.GEMINI_API_KEY:
        sys.exit("Set GEMINI_API_KEY in .env (see .env.example) or run with MOCK_LLM=1.")
    mode = "MOCK (simulated model)" if config.MOCK_LLM else f"Gemini ({config.GEMINI_MODEL})"
    print(f"Mode: {mode}")

    before = run("BEFORE: no defence layers", False, ATTACKS)
    after = run("AFTER: sanitiser + output validation + moderation", True, ATTACKS)
    extra = run("EXTRA ATTACK (protected)", True, EXTRA_ATTACKS)

    print(f"\n{LINE}\n  FALSE-POSITIVE CHECK (benign queries, protected pipeline)\n{LINE}")
    fp = []
    for q in BENIGN_QUERIES:
        r = chat(q)
        blocked = r["status"] != "answered"
        fp.append({"query": q, "blocked": blocked, "status": r["status"]})
        print(f"  {'BLOCKED (false positive)' if blocked else 'ok'}  <- {q}")

    print(f"\n{LINE}\n  MODERATION PROBES\n{LINE}")
    mp = []
    for t in MODERATION_PROBES:
        m = moderate_text(t)
        mp.append({"text": t, "flagged": m.flagged, "scores": m.scores})
        print(f"  flagged={m.flagged} scores={m.scores} <- {t}")

    n = len(ATTACKS)
    md = [f"# Day 34 results ({mode})", "",
          "| # | Category | Attack | Before | After | Stopped by |", "|---|---|---|---|---|---|"]
    for b, a in zip(before, after):
        md.append(f"| {b['id']} | {b['category']} | {b['name']} | {b['verdict']} | {a['verdict']} | {a['layer'] or 'model'} |")
    md += ["", "| Metric | Before | After |", "|---|---|---|",
           f"| Successful injection | {count(before,'INJECTED')}/{n} | {count(after,'INJECTED')}/{n} |",
           f"| Partial compliance | {count(before,'PARTIAL')}/{n} | {count(after,'PARTIAL')}/{n} |",
           f"| Blocked | {count(before,'BLOCKED')}/{n} | {count(after,'BLOCKED')}/{n} |",
           f"| Attack success rate | {count(before,'INJECTED')/n:.0%} | {count(after,'INJECTED')/n:.0%} |",
           "", f"False positives on benign queries: {sum(x['blocked'] for x in fp)}/{len(fp)}"]
    (OUT / "results.md").write_text("\n".join(md), encoding="utf-8")
    (OUT / "results.json").write_text(json.dumps(
        {"mode": mode, "before": before, "after": after, "extra": extra, "false_positives": fp, "moderation": mp},
        indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{LINE}\n  SUMMARY\n{LINE}\n" + "\n".join(md[-9:]))
    print(f"\nSaved: {OUT/'results.md'} and {OUT/'results.json'}")


if __name__ == "__main__":
    main()
