"""focused checks for the expert system's main behaviour and representation."""
import unittest

from cases.scenarios import SCENARIOS
from src.engine import next_question, run_inference
from src.explain import explain_results
from src.facts import ALL_FACTS, DERIVED_FACTS, PRIMITIVE_FACTS, new_facts
from src.frames import (DSLModemFrame, FibreONTFrame, NetworkEquipmentFrame,
                        RouterFrame, new_frame_store)
from src.questions import QUESTIONS, apply_answer, should_ask
from src.rules import DIAGNOSES, RULES

class KnowledgeBaseTests(unittest.TestCase):
    def test_rule_structure_and_source_traceability(self):
        self.assertEqual((len(RULES), len(DIAGNOSES), len(DERIVED_FACTS)), (23, 9, 4))
        self.assertEqual(len([r for r in RULES if "diagnosis" in r]), 19)
        self.assertEqual(len({r["id"] for r in RULES}), 23)
        for rule in RULES:
            self.assertTrue(rule.get("sources") and rule.get("explanation"))
            self.assertTrue("conditions" in rule or "any_of" in rule)
            self.assertTrue("diagnosis" in rule or "derive" in rule)

    def test_working_memory_starts_unknown_and_is_isolated(self):
        first, second = new_facts(), new_facts()
        self.assertEqual(set(first), set(ALL_FACTS))
        self.assertEqual(len(PRIMITIVE_FACTS), 30)
        self.assertTrue(all(value is None for value in first.values()))
        self.assertEqual(run_inference(first), {})
        first["device_scope"] = "all"
        self.assertIsNone(second["device_scope"])

    def test_invalid_question_answer_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_answer(new_facts(), "Q02", "maybe")

class InferenceTests(unittest.TestCase):
    def test_line_diagnosis_uses_shared_failure_and_direct_line_evidence(self):
        facts = new_facts()
        facts.update({"device_scope": "all", "wired_connection": "fails",
                      "broadband_light": "abnormal", "dsl_sync_drops": True})
        result = run_inference(facts)
        self.assertIn("line_fault", result)
        # R06 uses the DSL frame's equipment-specific interpretation it does not depend directly on a production-rule derivation in its trace.
        derivations = result["line_fault"]["derivations"]
        self.assertEqual(derivations, [])
        self.assertIn("R06", [item["id"] for item in result["line_fault"]["rules"]])

    def test_provider_outage_needs_household_scope_and_corroboration(self):
        facts = new_facts()
        facts.update({"device_scope": "all", "wired_connection": "fails",
                      "local_outage_reports": True, "provider_status_outage": False})
        result = run_inference(facts)
        self.assertIn("isp_outage", result)
        self.assertEqual([x["id"] for x in result["isp_outage"]["derivations"]],
                         ["R01", "R02", "R03"])
        facts["device_scope"] = "one"
        self.assertNotIn("isp_outage", run_inference(facts))
        self.assertIn("isp_outage", run_inference({**new_facts(), "provider_status_outage": True}))

    def test_account_diagnosis_requires_explicit_provider_restriction(self):
        facts = new_facts()
        facts.update({"device_scope": "all", "account_status": "active"})
        self.assertNotIn("account_issue", run_inference(facts))
        facts["account_status"] = "suspended"
        self.assertIn("account_issue", run_inference(facts))

    def test_device_diagnosis_requires_cross_network_failure(self):
        facts = new_facts()
        facts.update({"device_scope": "one", "device_fails_other_networks": False})
        self.assertNotIn("device_fault", run_inference(facts))
        facts["device_fails_other_networks"] = True
        self.assertIn("device_fault", run_inference(facts))

    def test_wifi_diagnosis_requires_wired_wireless_contrast(self):
        facts = new_facts()
        facts.update({"device_scope": "one", "wired_connection": "works",
                      "wifi_connection": "fails", "device_far_or_obstructed": True})
        self.assertIn("wifi_problem", run_inference(facts))
        facts["wired_connection"] = "fails"
        self.assertNotIn("wifi_problem", run_inference(facts))

    def test_congestion_requires_reported_slowdown_and_a_pattern(self):
        facts = new_facts()
        facts.update({"slowdown_reported": False, "heavy_household_use": True,
                      "peak_time_pattern": True})
        self.assertNotIn("congestion", run_inference(facts))
        facts["slowdown_reported"] = True
        self.assertIn("congestion", run_inference(facts))

    def test_access_equipment_recovery_is_not_labelled_as_router_fault(self):
        facts = new_facts()
        facts.update({"access_type": "copper", "device_scope": "all",
                      "incoming_cable_secure": True, "wired_connection": "fails",
                      "dsl_modem_restart_restored": True})
        result = run_inference(facts)
        self.assertIn("access_equipment_issue", result)
        self.assertNotIn("router_fault", result)

class ConflictAndQuestionTests(unittest.TestCase):
    def test_all_matching_diagnoses_are_reported_without_ranking(self):
        facts = new_facts()
        facts.update({"device_scope": "all", "provider_status_outage": True,
                      "account_status": "suspended"})
        results = run_inference(facts)
        self.assertIn("isp_outage", results)
        self.assertIn("account_issue", results)
        explanation = explain_results(results)
        self.assertIn("Possible explanation(s)", explanation)
        self.assertIn("Possible provider outage", explanation)
        self.assertIn("Account or service restriction", explanation)
        self.assertIn("rather than claiming that one is certain", explanation)

    def test_direct_and_contextual_evidence_can_produce_multiple_results(self):
        facts = new_facts()
        facts.update({"device_scope": "all", "wired_connection": "fails",
                      "local_outage_reports": True, "provider_status_outage": False,
                      "ont_link_status": "fault_indicator"})
        results = run_inference(facts)
        self.assertIn("line_fault", results)
        self.assertIn("isp_outage", results)

    def test_question_order_is_conditional_and_does_not_repeat(self):
        facts, asked = new_facts(), set()
        first = next_question(facts, asked)
        self.assertEqual(first["id"], "Q01")
        apply_answer(facts, "Q01", "full fibre (FTTP)")
        asked.add("Q01")
        second = next_question(facts, asked)
        self.assertIsNotNone(second)
        self.assertNotIn(second["id"], asked)
        self.assertFalse(should_ask(next(q for q in QUESTIONS if q["id"] == "Q17"),
                                    {**facts, "device_scope": "all"}))
        setup_facts = {**new_facts(), "access_type": "copper", "broadband_light": "abnormal",
                       "device_scope": "all", "wired_connection": "fails", "dsl_sync_drops": False}
        asked_before_q11 = {f"Q{i:02d}" for i in range(1, 11)}
        setup_question = next_question(setup_facts, asked_before_q11)
        self.assertEqual(setup_question["id"], "Q11")

    def test_all_sixteen_authored_scenarios_match_the_expected_outcome(self):
        for case in SCENARIOS:
            with self.subTest(case=case["id"]):
                facts, frames = new_facts(), new_frame_store()
                for qid, answer in case["answers"].items():
                    apply_answer(facts, qid, answer, frames=frames)
                results = run_inference(facts, frames=frames)
                expected = {case["expected"]} if case["expected"] else set()
                self.assertEqual(set(results), expected)
                if case.get("expected_rules"):
                    matched_rules = {rule["id"] for item in results.values() for rule in item["rules"]}
                    self.assertEqual(matched_rules, set(case["expected_rules"]))

    def test_no_diagnosis_explanation_recommends_escalation(self):
        explanation = explain_results({})
        self.assertIn("No diagnosis rule", explanation)
        self.assertIn("provider", explanation.lower())
        filter_explanation = explain_results({}, {"microfilter_status": "missing"})
        self.assertIn("Fit the correct filter", filter_explanation)
        self.assertIn("not, by itself, evidence", filter_explanation)
        ont_facts, ont_frames = new_facts(), new_frame_store()
        apply_answer(ont_facts, "Q01", "full fibre (FTTP)", frames=ont_frames)
        apply_answer(ont_facts, "Q05", "Nokia ONT: Power and PON steady green; Port indicator off", frames=ont_frames)
        self.assertEqual(ont_frames.ont.get_slot("lan_indicator"), "off")
        ont_explanation = explain_results({}, ont_frames.to_facts(ont_facts), ont_frames)
        self.assertIn("Port indicator is off", ont_explanation)
        self.assertIn("Check both ends", ont_explanation)
        self.assertIn("try another cable", ont_explanation)
        self.assertIn("does not, by itself, indicate a fibre-link fault", ont_explanation)
        q05 = next(q for q in QUESTIONS if q["id"] == "Q05")
        self.assertIn("ECI", q05["reason"])
        self.assertIn("not sure", q05["reason"])
        self.assertNotIn("Auto-Join", DIAGNOSES["wifi_authentication"]["advice"])

class FrameRepresentationTests(unittest.TestCase):
    def test_equipment_frames_share_slots_and_reject_invalid_equipment_slots(self):
        router, ont = RouterFrame(power_state=True), FibreONTFrame(connection_status="normal")
        self.assertIsInstance(router, NetworkEquipmentFrame)
        self.assertIsInstance(ont, NetworkEquipmentFrame)
        self.assertTrue(router.get_slot("power_state"))
        ont.set_slot("los_indicator", "red")
        self.assertEqual(ont.derive_link_status(), "fault_indicator")
        with self.assertRaises(KeyError):
            router.set_slot("los_indicator", "red")
        self.assertNotIn("dsl_sync_drops", ont.slot_definitions())

    def test_unknown_observations_remain_unknown_in_frame_slots(self):
        facts, frames = new_facts(), new_frame_store()
        apply_answer(facts, "Q02", "not sure", frames=frames)
        self.assertIsNone(frames.router.get_slot("power_state"))
        self.assertEqual(run_inference(facts, frames=frames), {})

    def test_access_type_selects_the_relevant_equipment_frame(self):
        facts, frames = new_facts(), new_frame_store()
        apply_answer(facts, "Q01", "full fibre (FTTP)", frames=frames)
        self.assertIsInstance(frames.ont, FibreONTFrame)
        self.assertIsNone(frames.dsl)
        dsl_facts, dsl_frames = new_facts(), new_frame_store()
        apply_answer(dsl_facts, "Q01", "copper/ADSL", frames=dsl_frames)
        self.assertIsInstance(dsl_frames.dsl, DSLModemFrame)

    def test_question_answers_populate_frames_used_by_the_rules(self):
        facts, frames = new_facts(), new_frame_store()
        apply_answer(facts, "Q01", "full fibre (FTTP)", frames=frames)
        apply_answer(facts, "Q05", "ONT: LOS red", frames=frames)
        self.assertEqual(frames.to_facts(facts)["ont_link_status"], "fault_indicator")
        result = run_inference(facts, frames=frames)
        self.assertIn("line_fault", result)
        self.assertIn("R10", [r["id"] for r in result["line_fault"]["rules"]])

    def test_ont_link_status_is_derived_from_indicator_slots(self):
        facts, frames = new_facts(), new_frame_store()
        apply_answer(facts, "Q01", "full fibre (FTTP)", frames=frames)
        apply_answer(facts, "Q05", "ONT: PON solid green and LOS off (normal)", frames=frames)
        self.assertEqual(frames.to_facts(facts)["ont_link_status"], "healthy")
        apply_answer(facts, "Q05", "ONT: PON and LOS both flashing", frames=frames)
        self.assertEqual(frames.to_facts(facts)["ont_link_status"], "fault_indicator")
        apply_answer(facts, "Q05", "ONT: PON flashing, LOS off (verification)", frames=frames)
        self.assertEqual(frames.to_facts(facts)["ont_link_status"], "verification")
        self.assertNotIn("line_fault", run_inference(facts, frames=frames))

        red_facts, red_frames = new_facts(), new_frame_store()
        apply_answer(red_facts, "Q01", "full fibre (FTTP)", frames=red_frames)
        apply_answer(red_facts, "Q05", "ONT: PON red (unclassified)", frames=red_frames)
        self.assertIsNone(red_frames.to_facts(red_facts)["ont_link_status"])
        self.assertNotIn("line_fault", run_inference(red_facts, frames=red_frames))

    def test_r06_requires_frame_derived_dsl_corroboration(self):
        facts = new_facts()
        facts.update({"device_scope": "all", "wired_connection": "fails",
                      "broadband_light": "abnormal"})
        self.assertNotIn("line_fault", run_inference(facts))

        facts["dsl_sync_drops"] = True
        facts["dial_tone"] = "clear"
        result = run_inference(facts)
        self.assertIn("line_fault", result)
        self.assertIn("R06", [rule["id"] for rule in result["line_fault"]["rules"]])

    def test_dsl_frame_derives_combined_line_evidence_for_r06(self):
        facts, frames = new_facts(), new_frame_store()
        apply_answer(facts, "Q01", "copper/ADSL", frames=frames)
        frames.set_fact("dsl_sync_drops", True)
        frames.set_fact("dial_tone", "poor")
        mapped = frames.to_facts(facts)
        self.assertEqual(mapped["dsl_line_evidence"], "corroborated")
        result = run_inference(facts, frames=frames)
        self.assertIn("R06", [rule["id"] for rule in result["line_fault"]["rules"]])

    def test_dsl_frame_waits_for_context_before_derived_line_evidence(self):
        facts, frames = new_facts(), new_frame_store()
        apply_answer(facts, "Q01", "copper/ADSL", frames=frames)
        frames.set_fact("dsl_sync_drops", True)
        frames.set_fact("dial_tone", "clear")
        self.assertIsNone(frames.to_facts(facts)["dsl_line_evidence"])
        facts.update({"device_scope": "all", "wired_connection": "fails",
                      "broadband_light": "abnormal"})
        frames.set_fact("device_scope", "all")
        frames.set_fact("wired_connection", "fails")
        frames.set_fact("broadband_light", "abnormal")
        # The first frame export has no R01 conclusion yet. inference derives shared failure, refreshes the frame procedure, and then evaluates R06.
        result = run_inference(facts, frames=frames)
        self.assertIn("line_fault", result)
        self.assertEqual(frames.to_facts({**facts, "shared_connection_failure": True})[
            "dsl_line_evidence"], "corroborated")

    def test_inherited_power_state_supplies_router_power_fact(self):
        facts, frames = new_facts(), new_frame_store()
        apply_answer(facts, "Q02", "no", frames=frames)
        apply_answer(facts, "Q03", "yes, all checked", frames=frames)
        self.assertFalse(frames.router.get_slot("power_state"))
        self.assertFalse(frames.to_facts(facts)["router_lights_on"])
        self.assertIn("router_fault", run_inference(facts, frames=frames))

    def test_fibre_consultation_can_reach_router_restart_question(self):
        facts, frames, asked = new_facts(), new_frame_store(), set()
        initial = {"Q01": "full fibre (FTTP)", "Q07": "all devices",
                   "Q08": "both fail", "Q06": "yes", "Q12": "no", "Q13": "no"}
        for qid, answer in initial.items():
            apply_answer(facts, qid, answer, frames=frames)
            asked.add(qid)
        for _ in range(27):
            question = next_question(facts, asked, frames=frames)
            if question is None or question["id"] == "Q23":
                break
            answer = "both normal" if question["id"] == "Q04" else question["options"][-1]
            apply_answer(facts, question["id"], answer, frames=frames)
            asked.add(question["id"])
        self.assertEqual(question["id"], "Q23")
        apply_answer(facts, "Q23", "yes, it returned", frames=frames)
        self.assertTrue(frames.to_facts(facts)["router_restart_restored"])

if __name__ == "__main__":
    unittest.main()
