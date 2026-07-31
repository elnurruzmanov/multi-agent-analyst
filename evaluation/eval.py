"""F11 — Evaluation harness.

Metrics per question:
- routing_ok: supervisor chose the expected agent
- contains_ok: answer/trace contains an expected substring (when defined)
- judge_score: LLM-as-judge 1-10 (skipped in mock mode -> heuristic)
Run `--no-critic` for the ablation table (quality with vs without critic).
"""

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config           # noqa: E402
import graph            # noqa: E402

QUESTIONS = json.load(open(os.path.join(os.path.dirname(__file__), "test_questions.json")))


def judge(question: str, answer: str) -> int:
    if config.MOCK:
        return 7 if len(answer) > 30 else 3
    raw = config.llm(
        f"Question: {question}\nAnswer: {answer}\n"
        'Score answer quality 1-10. Respond JSON: {"score": N}', json_mode=True)
    try:
        return int(json.loads(raw)["score"])
    except Exception:
        return 5


def main(use_critic: bool):
    rows = []
    for t in QUESTIONS:
        s = graph.ask(t["q"], use_critic=use_critic)
        routed = s.get("plan", [""])[0]
        blob = s.get("answer", "") + " " + " ".join(s.get("steps", [])) \
               + " " + " ".join(str(v) for k, v in s.items() if k.endswith("_out"))
        rows.append({
            "question": t["q"],
            "routed": routed,
            "routing_ok": int(routed == t["expect_agent"]),
            "contains_ok": int(t["must_contain"].lower() in blob.lower()) if t["must_contain"] else "",
            "judge_score": judge(t["q"], s.get("answer", "")),
        })
    out = os.path.join(os.path.dirname(__file__),
                       f"eval_results{'_no_critic' if not use_critic else ''}.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    r_ok = sum(r["routing_ok"] for r in rows)
    scores = [r["judge_score"] for r in rows]
    print(f"critic={'ON' if use_critic else 'OFF'} | routing {r_ok}/{len(rows)} | "
          f"judge avg {sum(scores)/len(scores):.1f} | saved {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-critic", action="store_true")
    main(use_critic=not ap.parse_args().no_critic)
