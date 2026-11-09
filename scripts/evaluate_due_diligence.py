from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Score Data Agent answers against deterministic facts")
    parser.add_argument("responses", type=Path)
    parser.add_argument("--questions-file", type=Path, default=Path("benchmark/due_diligence_questions.yaml"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    questions = yaml.safe_load(args.questions_file.read_text(encoding="utf-8"))["questions"]
    expected = {question["id"]: question for question in questions}
    rows = list(csv.DictReader(args.responses.open(encoding="utf-8-sig", newline="")))
    scored = []
    for row in rows:
        question = expected[row["question_id"]]
        answer = row["answer"]
        groups = question["required_groups"]
        matches = [bool(re.search(pattern, answer, flags=re.IGNORECASE)) for pattern in groups]
        matched = sum(matches)
        if row["success"].lower() != "true" or matched == 0:
            result = "incorrect"
        elif matched == len(groups):
            result = "correct"
        else:
            result = "partial"
        scored.append(
            {
                "question_id": row["question_id"],
                "question_class": row["question_class"],
                "repetition": int(row["repetition"]),
                "result": result,
                "matched_facts": matched,
                "required_facts": len(groups),
                "fact_recall": matched / len(groups),
                "total_seconds": float(row["total_seconds"]),
            }
        )

    result_counts = Counter(row["result"] for row in scored)
    class_counts: dict[str, Counter] = defaultdict(Counter)
    for row in scored:
        class_counts[row["question_class"]][row["result"]] += 1
    summary = {
        "responses_file": str(args.responses),
        "count": len(scored),
        "correct": result_counts["correct"],
        "partial": result_counts["partial"],
        "incorrect": result_counts["incorrect"],
        "full_accuracy": result_counts["correct"] / len(scored),
        "partial_credit_accuracy": (
            result_counts["correct"] + 0.5 * result_counts["partial"]
        )
        / len(scored),
        "mean_fact_recall": sum(row["fact_recall"] for row in scored) / len(scored),
        "by_class": {key: dict(value) for key, value in sorted(class_counts.items())},
        "questions": scored,
        "method": (
            "Case-insensitive regex matching against required deterministic facts. "
            "A human review remains necessary to detect contradictory extra claims."
        ),
    }
    output = args.output or args.responses.with_name(args.responses.stem.replace("-responses", "-accuracy") + ".json")
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
