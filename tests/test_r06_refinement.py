"""compare the archived R06/R07 path with the current frame dependent R06 rule."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import src.engine as engine
from src.facts import new_facts
from src.explain import explain_results

ROOT = Path(__file__).resolve().parents[1]
BASELINE_R06 = json.loads((ROOT / "history" / "r06_baseline_rule.json").read_text(encoding="utf-8"))
BASELINE_R07 = json.loads((ROOT / "history" / "r06_baseline_diagnostic_rule.json").read_text(encoding="utf-8"))

def run_with_archived_line_rules(facts):
    """Rebuild the saved 2 rule line path without changing current source."""
    derivations = copy.deepcopy(engine.DERIVATION_RULES) + [copy.deepcopy(BASELINE_R06)]
    diagnostics = [copy.deepcopy(rule) for rule in engine.DIAGNOSTIC_RULES if rule["id"] != "R06"]
    diagnostics.append(copy.deepcopy(BASELINE_R07))
    with patch.object(engine, "DERIVATION_RULES", derivations), patch.object(
        engine, "DIAGNOSTIC_RULES", diagnostics
    ):
        return engine.run_inference(facts)

class R06RefinementTests(unittest.TestCase):
    def test_revision_requires_dsl_sync_evidence_for_the_line_fault_path(self):
        facts = new_facts()
        facts.update({"device_scope": "all", "wired_connection": "fails",
                      "broadband_light": "abnormal", "local_outage_reports": True,
                      "provider_status_outage": False, "dsl_sync_drops": None})
        earlier, revised = run_with_archived_line_rules(facts), engine.run_inference(facts)
        self.assertIn("line_fault", earlier)
        self.assertNotIn("line_fault", revised)
        self.assertIn("isp_outage", revised)
        facts["dsl_sync_drops"] = True
        revised = engine.run_inference(facts)
        self.assertIn("line_fault", revised)
        self.assertIn("R06", [r["id"] for r in revised["line_fault"]["rules"]])

        # a missing required filter is problebly a local setup issue, not evidence of a provider line fault, even when the broadband indicator is abnormal.
        filter_facts = new_facts()
        filter_facts.update({"access_type": "copper", "broadband_light": "abnormal",
                             "microfilter_status": "missing"})
        filter_result = engine.run_inference(filter_facts)
        self.assertNotIn("line_fault", filter_result)
        self.assertIn("local setup issue", explain_results(filter_result, filter_facts).lower())

if __name__ == "__main__":
    unittest.main()
