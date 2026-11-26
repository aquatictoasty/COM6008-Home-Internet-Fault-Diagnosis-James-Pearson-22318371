"""check rule references, fact names and the corrected source mappings."""

import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.facts import ALL_FACTS, FRAME_DERIVED_FACTS
from src.frames import DSLModemFrame
from src.rules import DIAGNOSES, RULES

with (ROOT / "knowledge" / "source_register.csv").open(encoding="utf-8", newline="") as handle:
    source_rows = {row["SourceID"]: row for row in csv.DictReader(handle)}
sources = set(source_rows)

errors = []
ids = [rule["id"] for rule in RULES]
if len(RULES) != 23 or len(set(ids)) != 23:
    errors.append("The final knowledge base must contain 23 uniquely numbered rules")
if sum("derive" in rule for rule in RULES) != 4:
    errors.append("Expected four derivation rules")
if sum("diagnosis" in rule for rule in RULES) != 19:
    errors.append("Expected 19 diagnostic rules")
if FRAME_DERIVED_FACTS != ("dsl_line_evidence",):
    errors.append("Expected the DSL frame-derived line-evidence fact")
dsl_frame = DSLModemFrame(dsl_sync_drops=True, dial_tone="poor")
if dsl_frame.derive_line_evidence(None, None) != "corroborated":
    errors.append("DSL frame should recognise repeated signal loss with a poor phone line")
dsl_frame = DSLModemFrame(dsl_sync_drops=True, dial_tone="clear")
if dsl_frame.derive_line_evidence(True, "abnormal") != "corroborated":
    errors.append("DSL frame should recognise repeated signal loss with a failed household wired connection")

for rule in RULES:
    for source_id in rule["sources"]:
        if source_id not in sources:
            errors.append(f"{rule['id']} references missing source {source_id}")
    groups = [rule.get("conditions", {})] + rule.get("any_of", [])
    for group in groups:
        for fact_name in group:
            if fact_name not in ALL_FACTS:
                errors.append(f"{rule['id']} references unknown fact {fact_name}")
    if "diagnosis" in rule and rule["diagnosis"] not in DIAGNOSES:
        errors.append(f"{rule['id']} references unknown diagnosis {rule['diagnosis']}")

by_id = {rule["id"]: rule for rule in RULES}
if by_id["R05"]["sources"] != ["S01"]:
    errors.append("R05 wired-versus-Wi-Fi comparison must cite Ofcom S01 only")
if by_id["R14"]["sources"] != ["S08"] or by_id["R14"]["conditions"] != {"account_status": "suspended"}:
    errors.append("R14 must cite S08 and use explicit provider restriction as its sufficient condition")
if by_id["R16"]["sources"] != ["S01", "S10"] or by_id["R16"].get("any_of") != [{"device_scope": "one"}, {"device_scope": "some"}]:
    errors.append("R16 password-rejection rule must cite S01 and require one or some affected devices")
if by_id["R17"]["sources"] != ["S07"]:
    errors.append("R17 Auto-Join rule must cite S07 (Apple Auto-Join guidance)")
if by_id["R18"].get("any_of") != [{"device_scope": "one"}, {"device_scope": "some"}]:
    errors.append("R18 must not use distance as a whole-house Wi-Fi diagnosis")
if by_id["R24"].get("diagnosis") != "access_equipment_issue" or len(by_id["R24"].get("any_of", [])) != 3:
    errors.append("R24 must distinguish DSL and FTTP access-equipment restart evidence")
if by_id["R25"].get("conditions") != {"access_type": "copper", "recent_line_noise": True, "slowdown_reported": True}:
    errors.append("R25 must require copper access, recent line noise and reported slowdown")
if by_id["R10"]["sources"] != ["S03", "S14", "S15"]:
    errors.append("R10 ONT rule must cite the Openreach and BT PON/LOS guidance")
if by_id["R10"].get("conditions") != {"ont_link_status": "fault_indicator"}:
    errors.append("R10 must use the frame-derived ONT fault indicator")
if by_id["R06"].get("conditions") != {"dsl_line_evidence": "corroborated"}:
    errors.append("R06 must consume the DSL frame-derived evidence fact without direct-condition bypasses")

# checks the extraction sheet's source and rule links as well as the rule register.
with (ROOT / "knowledge" / "extraction.csv").open(encoding="utf-8", newline="") as handle:
    extraction_rows = list(csv.DictReader(handle))
for row in extraction_rows:
    for source_id in filter(None, row["SourceID"].split(";")):
        if source_id not in sources:
            errors.append(f"{row['EvidenceID']} references missing source {source_id}")
    for rule_id in filter(None, row["RuleLinks"].split(";")):
        if rule_id not in set(ids):
            errors.append(f"{row['EvidenceID']} references missing rule {rule_id}")

by_evidence = {row["EvidenceID"]: row for row in extraction_rows}
k06 = by_evidence["K06"]
if "project" not in k06["InterpretationForSystem"] or "not a diagnostic relationship" not in k06["InterpretationForSystem"]:
    errors.append("K06 must distinguish the project-designed R06 conjunction from direct source guidance")
if "loss of broadband synchronisation" in k06["StatementExtracted"]:
    errors.append("K06 must not attribute the R06 diagnostic relationship directly to Ofcom/BT")
k07 = by_evidence["K07"]
if k07["SourceID"] != "S03;S14;S15" or k07["RuleLinks"] != "R10":
    errors.append("K07 must map the Openreach/BT indicator evidence to R10")
if "PON flashing with LOS off" not in k07["InterpretationForSystem"] or "verification" not in k07["InterpretationForSystem"]:
    errors.append("K07 must distinguish the PON-flashing/LOS-off verification state")
if "PON flashing with LOS off" not in source_rows["S15"]["Use"] or "verification" not in source_rows["S15"]["Use"]:
    errors.append("S15 must record the PON-flashing/LOS-off verification state")
if by_evidence["K15"]["SourceID"] != "S07" or by_evidence["K15"]["RuleLinks"] != "R17":
    errors.append("K15 Auto-Join evidence must map to S07 and R17")
if by_evidence["K16"]["SourceID"] != "S01;S10" or by_evidence["K16"]["RuleLinks"] != "R16":
    errors.append("K16 password-rejection comparison must map to S01 and R16")
if by_id["R16"].get("conditions", {}).get("password_correction_restored") is not False:
    errors.append("R16 must require password rejection to persist after the correct password is re-entered")
if "password_correction_restored" not in ALL_FACTS:
    errors.append("The password-correction observation must be represented in working memory")
if by_evidence["K13"]["SourceID"] != "S08" or by_evidence["K13"]["RuleLinks"] != "R14":
    errors.append("K13 account-restriction evidence must map to S08 and R14")

from src.questions import QUESTIONS
question_ids = [q["id"] for q in QUESTIONS]
if question_ids != [f"Q{i:02d}" for i in range(1,28)]:
    errors.append("Question identifiers must be Q01-Q27 in order")
if by_evidence["K25"]["SourceID"] != "S02;S04;S09" or by_evidence["K25"]["RuleLinks"] != "R25":
    errors.append("K25 recent-line-noise evidence must map to S02/S04/S09 and R25")
if by_evidence["K09"]["RuleLinks"] or by_evidence["K09"]["Use"] != "Contextual":
    errors.append("K09 microfilter omission must remain a contextual setup check, not a line-fault rule")
if by_evidence["K14"]["RuleLinks"] != "R15":
    errors.append("K14 one-device comparison must map directly to R15")

# check that source guidance is distinguished from project designed tests.
if "project-designed cross-network check" not in by_evidence["K14"]["InterpretationForSystem"]:
    errors.append("K14 must distinguish Ofcom's device comparison from the project-designed cross-network test")
if "other Wi-Fi networks" in by_evidence["K14"]["StatementExtracted"]:
    errors.append("K14 must not attribute the cross-network test directly to Ofcom")
if "project-designed checks" not in by_evidence["K16"]["InterpretationForSystem"]:
    errors.append("K16 must identify password re-entry and other-device checks as project-designed")
if "does not establish that these occurred simultaneously" not in by_evidence["K16"]["StatementExtracted"]:
    errors.append("K16 must qualify the timing of mixed-device outcomes in the BT forum source")
if "all Ethernet Port lights off" not in source_rows["S15"]["Use"]:
    errors.append("S15 must record the Nokia Ethernet Port-off cable guidance")
if "ECI Optical states" not in source_rows["S15"]["Limitations"]:
    errors.append("S15 must disclose that ECI Optical states are not interpreted by Q05")
if "Auto-Join instructions apply to Apple devices" not in by_evidence["K15"]["InterpretationForSystem"]:
    errors.append("K15 must keep Apple's Auto-Join guidance device-specific")

from src.questions import QUESTIONS
q05 = next(q for q in QUESTIONS if q["id"] == "Q05")
if not any("Port indicator off" in option for option in q05["options"]):
    errors.append("Q05 must represent the Nokia Port-indicator-off condition")
if not any(update.get("ont", {}).get("lan_indicator") == "off" for update in q05.get("frame_updates", {}).values()):
    errors.append("Q05 must store the Nokia Port-indicator-off observation separately from PON/LOS")
if "Port indicator being off" not in q05["reason"]:
    errors.append("Q05 must explain the Nokia Port-indicator-off cable check")
if "ECI models use an Optical indicator" not in q05["reason"] or "not sure" not in q05["reason"]:
    errors.append("Q05 must leave unlisted ECI Optical layouts unknown")
from src.rules import DIAGNOSES
if "Auto-Join" in DIAGNOSES["wifi_authentication"]["advice"]:
    errors.append("Generic Wi-Fi authentication advice must not use Apple-specific Auto-Join terminology")
q16 = next(q for q in QUESTIONS if q["id"] == "Q16")
if "previously saved network does not reconnect automatically" not in q16["options"]:
    errors.append("Q16 must use general saved-network wording rather than Apple's Auto-Join term for all devices")

from cases.scenarios import SCENARIOS
sc03 = next(case for case in SCENARIOS if case["id"] == "SC03")
if sc03["answers"].get("Q07") != "some devices" or sc03.get("expected_rules") != ["R18"]:
    errors.append("SC03 must exercise the one/few-device R18 distance/obstacle rule")

with (ROOT / "cases" / "forum_cases.csv").open(encoding="utf-8", newline="") as handle:
    forum_cases = {row["case_id"]: row for row in csv.DictReader(handle)}
f15 = forum_cases["F15"]
if "inferred rather than explicitly confirmed" not in f15["evidence_grade"] or "Q17 is inferred" not in f15["notes"]:
    errors.append("F15 must disclose its inferred Q17 cross-device comparison")
if "only facts explicitly stated" in (ROOT / "scripts" / "evaluate_forum_cases.py").read_text(encoding="utf-8"):
    errors.append("Forum evaluation script must not claim all mapped answers are explicitly stated")
result_path = ROOT / "results" / "forum_evaluation.json"
if result_path.exists():
    import json
    evaluation = json.loads(result_path.read_text(encoding="utf-8"))
    sensitivity = evaluation.get("sensitivity_analysis", {})
    if sensitivity.get("case_id") != "F15" or sensitivity.get("inferred_answer_removed") != "Q17" or sensitivity.get("exact_matches") != 9 or sensitivity.get("scored_cases") != 16:
        errors.append("Forum evaluation must report the F15 Q17 sensitivity result as 9/16")

if errors:
    raise SystemExit("Traceability audit failed:\n- " + "\n- ".join(errors))
print("Traceability audit passed: 23 rules (4 derivation, 19 diagnostic); Q01-Q27; source links, attribution qualifications, ONT model limits, Nokia Port handling, F15 sensitivity and SC03 rule coverage resolve.")
