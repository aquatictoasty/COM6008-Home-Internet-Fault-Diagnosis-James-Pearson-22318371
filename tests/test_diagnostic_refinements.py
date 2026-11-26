"""Regression checks for the selector and diagnostic refinements."""
import unittest

from src.engine import next_question, run_inference
from src.facts import new_facts
from src.frames import new_frame_store
from src.questions import QUESTIONS, apply_answer, should_ask

class DiagnosticRefinementTests(unittest.TestCase):
    def test_possible_outage_does_not_hide_the_dsl_sync_question(self):
        facts, frames = new_facts(), new_frame_store()
        answers = {"Q01": "part-fibre (FTTC/VDSL)", "Q07": "all devices",
                   "Q08": "both fail", "Q12": "no", "Q13": "yes"}
        for qid, answer in answers.items():
            apply_answer(facts, qid, answer, frames=frames)
        asked = set(answers)
        selected = []
        for _ in range(30):
            question = next_question(facts, asked, frames=frames)
            if question is None:
                break
            selected.append(question["id"])
            asked.add(question["id"])
        self.assertIn("Q09", selected)

    def test_restart_question_is_matched_to_access_type(self):
        for access, expected, excluded, indicator in (
            ("full fibre (FTTP)", "Q25", "Q24", "ONT: PON solid green and LOS off (normal)"),
            ("copper/ADSL", "Q24", "Q25", "Separate modem: normal"),
        ):
            with self.subTest(access=access):
                facts, frames = new_facts(), new_frame_store()
                apply_answer(facts, "Q01", access, frames=frames)
                apply_answer(facts, "Q05", indicator, frames=frames)
                mapped = frames.to_facts(facts)
                questions = {q["id"]: q for q in QUESTIONS}
                self.assertTrue(should_ask(questions[expected], mapped))
                self.assertFalse(should_ask(questions[excluded], mapped))

                # Q05 must only offer equipment that belongs to this access type.
                from src.questions import available_options, display_options
                fibre_options = [value for value in available_options(questions["Q05"], mapped)
                                 if value.startswith("ONT:")]
                modem_options = [value for value in available_options(questions["Q05"], mapped)
                                 if value.startswith("Separate modem:")]
                if access == "full fibre (FTTP)":
                    self.assertTrue(fibre_options)
                    self.assertFalse(modem_options)
                    self.assertTrue(any("Fibre box" in label for label in display_options(questions["Q05"], mapped)))
                    with self.assertRaises(ValueError):
                        apply_answer(facts, "Q05", "Separate modem: abnormal", frames=frames)
                else:
                    self.assertFalse(fibre_options)
                    self.assertTrue(modem_options)
                    self.assertTrue(any("Separate modem" in label for label in display_options(questions["Q05"], mapped)))
                    with self.assertRaises(ValueError):
                        apply_answer(facts, "Q05", "ONT: LOS red", frames=frames)

                # Q05 must only offer equipment that belongs to this access type.
                from src.questions import available_options, display_options
                fibre_options = [value for value in available_options(questions["Q05"], mapped)
                                 if value.startswith("ONT:")]
                modem_options = [value for value in available_options(questions["Q05"], mapped)
                                 if value.startswith("Separate modem:")]
                if access == "full fibre (FTTP)":
                    self.assertTrue(fibre_options)
                    self.assertFalse(modem_options)
                    self.assertTrue(any("Fibre box" in label for label in display_options(questions["Q05"], mapped)))
                    with self.assertRaises(ValueError):
                        apply_answer(facts, "Q05", "Separate modem: abnormal", frames=frames)
                else:
                    self.assertFalse(fibre_options)
                    self.assertTrue(modem_options)
                    self.assertTrue(any("Separate modem" in label for label in display_options(questions["Q05"], mapped)))
                    with self.assertRaises(ValueError):
                        apply_answer(facts, "Q05", "ONT: LOS red", frames=frames)

    def test_modem_or_ont_recovery_does_not_create_a_router_fault(self):
        cases = (
            {"Q01": "full fibre (FTTP)", "Q05": "ONT: PON solid green and LOS off (normal)",
             "Q07": "all devices", "Q06": "yes", "Q25": "yes, it restored service"},
            {"Q01": "copper/ADSL", "Q05": "Separate modem: normal",
             "Q07": "all devices", "Q06": "yes", "Q24": "yes, it restored service"},
        )
        for answers in cases:
            with self.subTest(access=answers["Q01"]):
                facts, frames = new_facts(), new_frame_store()
                for qid, answer in answers.items():
                    apply_answer(facts, qid, answer, frames=frames)
                result = run_inference(facts, frames=frames)
                self.assertIn("access_equipment_issue", result)
                self.assertNotIn("router_fault", result)

    def test_r11_and_r25_require_their_specific_line_evidence(self):
        # R11 needs repeated DSL sync loss that remains after a router restart.
        r11_cases = (
            (True, False, True),
            (True, True, False),
            (False, False, False),
            (None, False, False),
        )
        for sync_drops, restart_restored, expected in r11_cases:
            with self.subTest(sync_drops=sync_drops, restart_restored=restart_restored):
                dsl_facts = new_facts()
                dsl_facts.update({
                    "dsl_sync_drops": sync_drops,
                    "router_restart_restored": restart_restored,
                })
                dsl_result = run_inference(dsl_facts)
                line_rule_ids = [
                    rule["id"] for item in dsl_result.values() for rule in item["rules"]
                ]
                self.assertEqual("R11" in line_rule_ids, expected)

        facts, frames = new_facts(), new_frame_store()
        apply_answer(facts, "Q01", "copper/ADSL", frames=frames)
        apply_answer(facts, "Q10", "clear", frames=frames)
        apply_answer(facts, "Q20", "yes", frames=frames)
        apply_answer(facts, "Q26", "yes, recently", frames=frames)
        self.assertIs(facts["recent_line_noise"], True)
        self.assertEqual(facts["dial_tone"], "clear")
        result = run_inference(facts, frames=frames)
        self.assertIn("R25", [r["id"] for r in result["line_fault"]["rules"]])

        for evidence in (False, None):
            with self.subTest(recent_noise=evidence):
                negative = new_facts()
                negative.update({"access_type": "copper", "slowdown_reported": True,
                                 "recent_line_noise": evidence})
                ids = [r["id"] for item in run_inference(negative).values() for r in item["rules"]]
                self.assertNotIn("R25", ids)

    def test_password_rejection_applies_to_one_or_some_but_not_all_devices(self):
        facts = new_facts()
        facts.update({"wifi_join_status": "password_rejected", "another_device_connects": True,
                      "password_correction_restored": False})
        for scope in ("one", "some"):
            facts["device_scope"] = scope
            self.assertIn("wifi_authentication", run_inference(facts))
        facts["device_scope"] = "all"
        self.assertNotIn("wifi_authentication", run_inference(facts))

        # A successful password correction is evidence of a resolved credential entry, not a persistent authentication fault.
        from src.explain import explain_results
        facts["device_scope"] = "one"
        facts["password_correction_restored"] = True
        self.assertNotIn("wifi_authentication", run_inference(facts))
        explanation = explain_results(run_inference(facts), facts)
        self.assertIn("connected after the correct password was re-entered", explanation)

        # The consultation must ask Q27 once password rejection and a working comparison device are known. The answer is retained as an observation.
        from src.questions import QUESTIONS
        from src.engine import next_question
        from src.frames import new_frame_store
        facts, frames = new_facts(), new_frame_store()
        apply_answer(facts, "Q07", "one device", frames=frames)
        apply_answer(facts, "Q16", "password is rejected", frames=frames)
        apply_answer(facts, "Q17", "yes", frames=frames)
        q27 = next(q for q in QUESTIONS if q["id"] == "Q27")
        self.assertTrue(should_ask(q27, frames.to_facts(facts)))
        asked = {q["id"] for q in QUESTIONS if q["id"] != "Q27"}
        selected = next_question(facts, asked, frames=frames)
        self.assertEqual(selected["id"], "Q27")
        apply_answer(facts, "Q27", "yes, it connected", frames=frames)
        self.assertIs(facts["password_correction_restored"], True)
        self.assertNotIn("wifi_authentication", run_inference(facts, frames=frames))

if __name__ == "__main__":
    unittest.main()
