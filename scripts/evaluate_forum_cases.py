"""evaluates forum cases using conservative mappings and separate no data records.

Forum labels are reported causes or fixes. Most answers use details stated in the posts. F15 is a
qualified exception because Q17 is inferred from mixed device outcomes. the
script reports the full mapping and a sensitivity result with Q17 left unknown. A thread with no mapped answers is not counted as evidence that the system made
any meaningful abstention decision.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.engine import run_inference
from src.facts import new_facts
from src.frames import new_frame_store
from src.questions import apply_answer
from src.rules import DIAGNOSTIC_RULES

rows = []
with (ROOT / "cases" / "forum_cases.csv").open(encoding="utf-8", newline="") as handle:
    for case in csv.DictReader(handle):
        facts = new_facts()
        frames = new_frame_store()
        answers = json.loads(case["answers"])
        for question_id, answer in answers.items():
            apply_answer(facts, question_id, answer, frames=frames)

        results = run_inference(facts, frames=frames)
        actual = sorted(results)
        expected = case["expected"]
        eligible = expected not in {"out_of_scope", "unresolved", "insufficient_evidence"}

        if expected == "insufficient_evidence":
            status = "excluded: insufficient mapping evidence"
        elif expected == "no_diagnosis" and not actual:
            status = "matched"
        elif expected in actual and len(actual) == 1:
            status = "matched"
        elif expected in actual:
            status = "partly matched"
        elif not actual:
            status = "no diagnosis"
        else:
            status = "wrong"

        scope_case = expected in {"out_of_scope", "unresolved"}
        scope_boundary_abstention = scope_case and not actual and bool(answers)
        no_answer_record = not answers
        rows.append({
            "case_id": case["case_id"],
            "split": case["split"],
            "platform": case["platform"],
            "title": case["title"],
            "url": case["url"],
            "expected": expected,
            "actual": actual,
            "status": status,
            "evaluation_eligible": eligible,
            "scope_boundary_abstention_with_mapped_answers": scope_boundary_abstention,
            "no_mapped_answers": no_answer_record,
            "matched_rules": {
                diagnosis: [rule["id"] for rule in item["rules"]]
                for diagnosis, item in results.items()
            },
            "mapped_question_ids": sorted(answers),
            "evidence_grade": case["evidence_grade"],
            "notes": case["notes"],
        })

summary = {}
for split in ("development", "holdout"):
    subset = [row for row in rows if row["split"] == split]
    eligible = [row for row in subset if row["evaluation_eligible"]]
    matched = sum(row["status"] == "matched" for row in eligible)
    covered_rules = sorted({
        rule_id
        for row in eligible
        for rule_ids in row["matched_rules"].values()
        for rule_id in rule_ids
    })
    summary[split] = {
        "total_cases": len(subset),
        "scored_in_scope_cases": len(eligible),
        "diagnostic_rules_covered": covered_rules,
        "diagnostic_rules_covered_count": len(covered_rules),
        "diagnostic_rule_coverage_rate": round(len(covered_rules) / len(DIAGNOSTIC_RULES), 3),
        "matched": matched,
        "partly_matched": sum(row["status"] == "partly matched" for row in eligible),
        "no_diagnosis": sum(row["status"] == "no diagnosis" for row in eligible),
        "wrong": sum(row["status"] == "wrong" for row in eligible),
        "scope_boundary_abstentions_with_mapped_answers": sum(
            row["scope_boundary_abstention_with_mapped_answers"] for row in subset
        ),
        "records_with_no_mapped_answers": sum(row["no_mapped_answers"] for row in subset),
        "excluded_insufficient_evidence": sum(
            row["expected"] == "insufficient_evidence" for row in subset
        ),
        "exact_match_rate": round(matched / len(eligible), 3) if eligible else None,
    }

all_scored = [row for row in rows if row["evaluation_eligible"]]
all_covered_rules = sorted({
    rule_id
    for row in all_scored
    for rule_ids in row["matched_rules"].values()
    for rule_id in rule_ids
})
summary["overall"] = {
    "total_cases": len(rows),
    "scored_in_scope_cases": len(all_scored),
    "matched": sum(row["status"] == "matched" for row in all_scored),
    "partly_matched": sum(row["status"] == "partly matched" for row in all_scored),
    "no_diagnosis": sum(row["status"] == "no diagnosis" for row in all_scored),
    "wrong": sum(row["status"] == "wrong" for row in all_scored),
    "diagnostic_rules_covered": all_covered_rules,
    "diagnostic_rules_covered_count": len(all_covered_rules),
    "diagnostic_rule_coverage_rate": round(len(all_covered_rules) / len(DIAGNOSTIC_RULES), 3),
    "exact_match_rate": round(sum(row["status"] == "matched" for row in all_scored) / len(all_scored), 3) if all_scored else None,
}

# F15 includes one inferred Q17 answer. Re run that case with Q17 unknown to show how the single inference affects the overall exact match result.
f15_case = next(case for case in csv.DictReader((ROOT / "cases" / "forum_cases.csv").open(encoding="utf-8", newline="")) if case["case_id"] == "F15")
f15_answers = json.loads(f15_case["answers"])
f15_answers.pop("Q17", None)
f15_facts = new_facts()
f15_frames = new_frame_store()
for question_id, answer in f15_answers.items():
    apply_answer(f15_facts, question_id, answer, frames=f15_frames)
f15_sensitivity_results = run_inference(f15_facts, frames=f15_frames)
f15_expected = f15_case["expected"]
f15_sensitivity_match = f15_expected in f15_sensitivity_results and len(f15_sensitivity_results) == 1
f15_primary = next(row for row in rows if row["case_id"] == "F15")
primary_f15_match = f15_primary["status"] == "matched"
sensitivity_matches = summary["overall"]["matched"] - int(primary_f15_match) + int(f15_sensitivity_match)
sensitivity = {
    "case_id": "F15",
    "inferred_answer_removed": "Q17",
    "alternative_answer": "unknown (not mapped)",
    "actual_diagnoses_without_inference": sorted(f15_sensitivity_results),
    "scored_cases": summary["overall"]["scored_in_scope_cases"],
    "exact_matches": sensitivity_matches,
    "exact_match_rate": round(sensitivity_matches / summary["overall"]["scored_in_scope_cases"], 4),
    "percentage": round(100 * sensitivity_matches / summary["overall"]["scored_in_scope_cases"], 2),
}

output = {
    "dataset": "20 public broadband/network forum threads; 12 development and 8 second-phase challenge cases",
    "case_access_dates": "Recorded separately for each case in cases/forum_cases.csv",
    "summary": summary,
    "sensitivity_analysis": sensitivity,
    "cases": rows,
    "method_notes": [
        "Mappings use stated facts where available. F15 is a disclosed exception: Q17 is inferred from mixed device outcomes because the thread does not confirm simultaneous successful and failed connections. a sensitivity result leaves Q17 unknown.",
        "F01 reports a later line replacement but omits access type and explicit DSL synchronisation loss. it is excluded from scoring.",
        "Reported fixes are used as case labels. ",
        "An explicit expected no_diagnosis label is scored as a correct abstention only when mapped in scope symptoms are present and the case evidence does not support one of the available diagnoses.",
        "Threads with no mapped answers are recorded as no data examples and do not demonstrate that the engine meaningfully abstained.",
        "Development cases informed selected question/ rule refinements. The 8 second phase challenge cases (CSV split value `holdout`) were not used to alter anyy rules or answer mappings.",
        "thee second phase case set was reviewed for mapped answer overlap. F14 and F18 replaced cases after this review, so the set is a second phase challenge rather than a blind or fully independent holdout.",
        "F19 remains a scored miss: the post confirms that access returned after the correct password was entered. Q27 records this recovery, and R16 requires the correct password to remain rejected after re entry. The system abstains rather than assigning a persistent authentication fault. A separate credential-entry outcome is not justified by one case.",
        "The forum set is a convenience sample and is used to challenge selected rules andd not estimate population performance.",
    ],
}

(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "results" / "forum_evaluation.json").write_text(
    json.dumps(output, indent=2), encoding="utf-8"
)
print("Forum challenge-set evaluation")
for split, values in summary.items():
    if split == "overall":
        print(f"overall: {values['total_cases']} total; {values['scored_in_scope_cases']} scored; {values['matched']} exact matches; rule coverage={values['diagnostic_rules_covered_count']}/{len(DIAGNOSTIC_RULES)} ({values['diagnostic_rule_coverage_rate']})")
        print(f"sensitivity without inferred F15 Q17: {sensitivity['exact_matches']}/{sensitivity['scored_cases']} exact matches ({sensitivity['percentage']}%)")
        continue
    display_split = "second-phase challenge" if split == "holdout" else split
    print(
        f"{display_split}: {values['total_cases']} total; "
        f"{values['scored_in_scope_cases']} scored; matched={values['matched']}; "
        f"partial={values['partly_matched']}; no diagnosis={values['no_diagnosis']}; "
        f"wrong={values['wrong']}; "
        f"mapped-answer boundary abstentions={values['scope_boundary_abstentions_with_mapped_answers']}; "
        f"no-answer records={values['records_with_no_mapped_answers']}; "
        f"excluded={values['excluded_insufficient_evidence']}; "
        f"exact={values['exact_match_rate']}"
    )
