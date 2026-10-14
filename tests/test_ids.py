import datetime as dt
import hashlib
import unittest

from core import ids


class TestIds(unittest.TestCase):
    def test_email_intent_hash_matches_spec(self):
        # A p.4: sha256(thread_id|last_msg_id|intent_idx)
        expected = hashlib.sha256(b"t1|m9|0").hexdigest()
        self.assertEqual(ids.email_intent_hash("t1", "m9", 0), expected)

    def test_split_intents_get_different_hashes(self):
        # A p.1: one row per intent (cases 5a/5b)
        self.assertNotEqual(ids.email_intent_hash("t1", "m9", 0), ids.email_intent_hash("t1", "m9", 1))

    def test_email_hash_rejects_missing_parts(self):
        with self.assertRaises(ValueError):
            ids.email_intent_hash("", "m9", 0)

    def test_task_hash_ignores_case_spacing_punctuation(self):
        a = ids.task_intent_hash("CON", "Rebuild  retainer pricing!")
        b = ids.task_intent_hash("CON", "rebuild retainer pricing")
        self.assertEqual(a, b)
        self.assertNotEqual(a, ids.task_intent_hash("CAR", "rebuild retainer pricing"))

    def test_timestamp_comes_from_internal_date(self):
        # 2026-10-14T07:54:00Z == 00:54 PDT
        ms = int(dt.datetime(2026, 10, 14, 7, 54, tzinfo=dt.timezone.utc).timestamp() * 1000)
        self.assertEqual(ids.timestamp_from_internal_date(str(ms)), "2026-10-14T00:54:00-07:00")

    def test_next_id_is_computed_from_existing(self):
        day = dt.date(2026, 10, 14)
        existing = ["T-20261014-CON-01", "T-20261014-CON-02", "T-20261014-CAR-05", "T-20261013-CON-09"]
        self.assertEqual(ids.next_id("T", "CON", day, existing), "T-20261014-CON-03")
        self.assertEqual(ids.next_id("T", "PER", day, existing), "T-20261014-PER-01")
        self.assertEqual(ids.next_id("IN", "CON", day, existing), "IN-20261014-CON-01")

    def test_next_id_rejects_unknown_area(self):
        with self.assertRaises(ValueError):
            ids.next_id("T", "XYZ", dt.date(2026, 10, 14), [])

    def test_placeholder_ids_from_b_are_invalid(self):
        # B p.13/p.17 used readable placeholders; A p.1 flags them
        self.assertFalse(ids.is_valid_id("hash_con_cdi_license_check"))
        self.assertTrue(ids.is_valid_id("T-20261014-CON-01"))


if __name__ == "__main__":
    unittest.main()
