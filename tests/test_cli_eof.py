"""Check that end of input cancels a consultation safely."""
from contextlib import redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch

from src.cli import run_session

class CliEndOfInputTests(unittest.TestCase):
    def test_eof_before_or_during_answers_cancels_without_diagnosis(self):
        message = "Input ended. The consultation has been cancelled without producing a diagnosis."
        for supplied_answers in ([], ["4"]):
            with self.subTest(supplied_answers=supplied_answers):
                output = StringIO()
                with patch("builtins.input", side_effect=[*supplied_answers, EOFError]):
                    with redirect_stdout(output):
                        facts, results = run_session()
                self.assertEqual(results, {})
                self.assertIn(message, output.getvalue())
                if supplied_answers:
                    self.assertEqual(facts["access_type"], "unknown")

if __name__ == "__main__":
    unittest.main()
