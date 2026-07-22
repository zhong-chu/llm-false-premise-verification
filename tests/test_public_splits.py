"""Offline integrity checks for the frozen public KG-FPQ splits."""

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "kgfpq"


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def source_record_id(row):
    """Support the original frozen split and newer splits with explicit metadata."""
    return row.get("source_record_id") or row["id"].split("-", 3)[3]


class FrozenSplitTests(unittest.TestCase):
    def test_primary_split_is_balanced_false_premise_data(self):
        rows = load_jsonl(DATA / "test_360.jsonl")
        self.assertEqual(len(rows), 360)
        self.assertTrue(all(row["expected"] == "NO" for row in rows))
        counts = Counter((row["domain"], row["confusability_level"]) for row in rows)
        self.assertEqual(set(counts), {(domain, level) for domain in ("art", "people", "place") for level in range(1, 7)})
        self.assertTrue(all(count == 20 for count in counts.values()))

    def test_replication_source_records_do_not_overlap_primary(self):
        primary = load_jsonl(DATA / "test_360.jsonl")
        replication = load_jsonl(DATA / "replication_360.jsonl")
        primary_sources = {(row["domain"], source_record_id(row)) for row in primary}
        replication_sources = {(row["domain"], source_record_id(row)) for row in replication}
        self.assertEqual(len(replication), 360)
        self.assertFalse(primary_sources & replication_sources)

    def test_mixed_split_has_paired_true_and_false_questions(self):
        rows = load_jsonl(DATA / "replication_mixed_720.jsonl")
        self.assertEqual(len(rows), 720)
        self.assertEqual(Counter(row["expected"] for row in rows), {"YES": 360, "NO": 360})
        self.assertEqual(Counter(row["polarity"] for row in rows), {"true": 360, "false": 360})


if __name__ == "__main__":
    unittest.main()
