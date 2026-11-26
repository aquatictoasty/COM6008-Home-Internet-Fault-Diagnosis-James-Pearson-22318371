"""a simple forward chaining inference and the ordered conditional questions."""

from .rules import DIAGNOSES, DERIVATION_RULES, DIAGNOSTIC_RULES

def _matches_group(group: dict, facts: dict) -> bool:
    """Return True when every fact in a condition group has the required value."""
    return all(facts.get(name) == value for name, value in group.items())

def rule_matches(rule: dict, facts: dict) -> bool:
    """Match a rule's required conditions and any optional alternative group."""
    if not _matches_group(rule.get("conditions", {}), facts):
        return False
    alternatives = rule.get("any_of", [])
    return not alternatives or any(_matches_group(group, facts) for group in alternatives)

def next_question(facts: dict, asked_questions: set[str] | None = None, frames=None) -> dict | None:
    """Return the next unanswered question whose simple conditions are met."""
    from .questions import QUESTIONS, should_ask

    if frames is not None:
        facts = frames.to_facts(facts)
    asked = asked_questions or set()

    # questions are asked in a fixed order. Their ask_if conditions skip checks that do not apply to the connection type or symptoms reported so far.
    for question in QUESTIONS:
        if question["id"] not in asked and should_ask(question, facts):
            return question
    return None

def _rule_fact_names(rule: dict) -> set[str]:
    names = set(rule.get("conditions", {}))
    for group in rule.get("any_of", []):
        names.update(group)
    return names

def _supporting_derivations(rule: dict, fired_rules: list[dict]) -> list[dict]:
    """Return the earlier rules that helped create facts used by this diagnosis."""
    needed = _rule_fact_names(rule)
    supporting = []

    # work backwards through the short list of facts created during inference.
    for earlier in reversed(fired_rules):
        if earlier["derive"] in needed:
            supporting.append(earlier)
            needed.update(earlier.get("conditions", {}))

    return sorted(supporting, key=lambda item: (item["round"], item["id"]))

def run_inference(facts: dict, frames=None) -> dict:
    """Apply derivation rules until no new facts can be added, then diagnose."""
    dsl_frame = None
    if frames is not None:
        working = frames.to_facts(facts)
    else:
        # usess the same copper line check when no frames are supplied.
        from .frames import DSLModemFrame

        dsl_frame = DSLModemFrame()
        for slot in (
            "dsl_sync_drops", "dial_tone", "recent_line_noise",
            "microfilter_status", "dsl_modem_restart_restored",
        ):
            value = facts.get(slot)
            if value is not None:
                dsl_frame.set_slot(slot, value)
        working = dict(facts)
        working["dsl_line_evidence"] = dsl_frame.derive_line_evidence(
            working.get("shared_connection_failure"), working.get("broadband_light")
        )

    fired_rules = []
    round_number = 0

    while True:
        new_facts = []
        for rule in DERIVATION_RULES:
            fact_name = rule["derive"]
            if working.get(fact_name) is None and rule_matches(rule, working):
                new_facts.append((fact_name, rule))

        if not new_facts:
            break

        round_number += 1
        for fact_name, rule in new_facts:
            working[fact_name] = rule.get("derive_value", True)
            fired_rules.append({**rule, "round": round_number})

        # the modem frame can use the shared failure fact created in an earlier round, so refresh its result after each round of rules.
        if frames is not None:
            working = frames.to_facts(working)
        elif dsl_frame is not None:
            working["dsl_line_evidence"] = dsl_frame.derive_line_evidence(
                working.get("shared_connection_failure"), working.get("broadband_light")
            )

    results = {}
    for rule in DIAGNOSTIC_RULES:
        if not rule_matches(rule, working):
            continue

        diagnosis_id = rule["diagnosis"]
        if diagnosis_id not in results:
            results[diagnosis_id] = {
                "details": DIAGNOSES[diagnosis_id],
                "rules": [],
                "derivations": [],
            }

        item = results[diagnosis_id]
        item["rules"].append(rule)
        for earlier in _supporting_derivations(rule, fired_rules):
            if all(existing["id"] != earlier["id"] for existing in item["derivations"]):
                item["derivations"].append(earlier)

    for item in results.values():
        item["rules"].sort(key=lambda row: row["id"])
        item["derivations"].sort(key=lambda row: (row["round"], row["id"]))

    # do not rank diagnoses. every matched result is a possible explanation.
    return dict(sorted(results.items()))
