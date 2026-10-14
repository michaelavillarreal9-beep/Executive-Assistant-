import unittest

from core import redact


class TestRedact(unittest.TestCase):
    def test_ssn_masked(self):
        self.assertNotIn("123-45-6789", redact.redact("SSN 123-45-6789 on file"))

    def test_labelled_numbers_masked(self):
        for text in ["Account #: 99887766", "routing 021000021", "Policy No. HO-55512",
                     "License: 0K12345", "claim number CLM-2026-0001"]:
            with self.subTest(text=text):
                out = redact.redact(text)
                self.assertIn("[MASKED]", out, out)

    def test_long_digit_runs_masked(self):
        self.assertIn("[NUMBER]", redact.redact("card 4111 1111 1111 1111 declined"))

    def test_email_keeps_domain_only(self):
        out = redact.redact("from jane.doe@example.com")
        self.assertEqual(out, "from [someone]@example.com")

    def test_amount_buckets(self):
        # A p.3: under $100, $100 to $1k, over $1k
        self.assertEqual(redact.amount_bucket(99.99), "UNDER_100")
        self.assertEqual(redact.amount_bucket(100), "100_TO_1K")
        self.assertEqual(redact.amount_bucket(1000), "100_TO_1K")
        self.assertEqual(redact.amount_bucket(1000.01), "OVER_1K")
        self.assertEqual(redact.redact("balance $2,450.00 due"), "balance [AMOUNT:OVER_1K] due")

    def test_snippet_is_at_most_200_chars(self):
        s = redact.snippet("word " * 200)
        self.assertLessEqual(len(s), redact.SNIPPET_MAX)

    def test_sensitive_threads_keep_reference_only(self):
        # A p.3: legal and financial threads store the reference only
        self.assertEqual(redact.snippet("full legal body text", sensitive=True), "[REFERENCE ONLY]")

    def test_plain_text_untouched(self):
        self.assertEqual(redact.redact("Choir rehearsal moved to Thursday"), "Choir rehearsal moved to Thursday")


if __name__ == "__main__":
    unittest.main()
