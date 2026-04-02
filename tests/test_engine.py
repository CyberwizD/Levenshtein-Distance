import unittest

from Levenshtein_Distance.engine import (
    DATE_PARTS,
    EXACT_MATCH,
    TEXT_SIMILARITY,
    active_weight_total,
    compare_records,
    default_field_configs,
    score_field,
    text_similarity,
)


class EngineTests(unittest.TestCase):
    def test_text_similarity_exact_match(self):
        self.assertEqual(text_similarity("John", "John"), 1.0)

    def test_text_similarity_insertion(self):
        self.assertAlmostEqual(text_similarity("john", "johne"), 0.8)

    def test_text_similarity_substitution(self):
        self.assertAlmostEqual(text_similarity("hassan", "hasan"), 5 / 6, places=4)

    def test_text_similarity_empty_string(self):
        self.assertEqual(text_similarity("", "john"), 0.0)

    def test_text_similarity_normalizes_case_and_spaces(self):
        self.assertEqual(text_similarity("  JOHN ", "john"), 1.0)

    def test_weight_total(self):
        self.assertEqual(active_weight_total(default_field_configs()), 100.0)

    def test_date_parts_full_match(self):
        breakdown = score_field(
            field_config=type("FieldConfigShim", (), {"key": "dob", "label": "DOB", "comparator": DATE_PARTS, "weight": 20.0})(),
            left_value="2024-04-02",
            right_value="02/04/2024",
        )
        self.assertEqual(breakdown.score, 20.0)
        self.assertTrue(breakdown.matched)

    def test_date_parts_year_only_mismatch(self):
        breakdown = score_field(
            field_config=type("FieldConfigShim", (), {"key": "dob", "label": "DOB", "comparator": DATE_PARTS, "weight": 20.0})(),
            left_value="2024-04-02",
            right_value="2023-04-02",
        )
        self.assertEqual(breakdown.score, 10.0)
        self.assertFalse(breakdown.matched)

    def test_date_parts_month_only_mismatch(self):
        breakdown = score_field(
            field_config=type("FieldConfigShim", (), {"key": "dob", "label": "DOB", "comparator": DATE_PARTS, "weight": 20.0})(),
            left_value="2024-04-02",
            right_value="2024-05-02",
        )
        self.assertEqual(breakdown.score, 15.0)

    def test_date_parts_day_only_mismatch(self):
        breakdown = score_field(
            field_config=type("FieldConfigShim", (), {"key": "dob", "label": "DOB", "comparator": DATE_PARTS, "weight": 20.0})(),
            left_value="2024-04-02",
            right_value="2024-04-03",
        )
        self.assertEqual(breakdown.score, 15.0)

    def test_date_parts_invalid_value(self):
        breakdown = score_field(
            field_config=type("FieldConfigShim", (), {"key": "dob", "label": "DOB", "comparator": DATE_PARTS, "weight": 20.0})(),
            left_value="2024-04-02",
            right_value="31/31/2024",
        )
        self.assertEqual(breakdown.score, 0.0)
        self.assertIn("invalid date", " ".join(breakdown.details).lower())

    def test_compare_records_mixes_text_exact_and_date(self):
        field_configs = [
            {"key": "first_name", "label": "First Name", "comparator": TEXT_SIMILARITY, "weight": 30.0, "active": True},
            {"key": "gender", "label": "Gender", "comparator": EXACT_MATCH, "weight": 20.0, "active": True},
            {"key": "date_of_birth", "label": "DOB", "comparator": DATE_PARTS, "weight": 50.0, "active": True},
        ]
        result = compare_records(
            phone_key="08030000001",
            dataset_a_record={"first_name": "John", "gender": "Male", "dob": "2024-04-02"},
            dataset_b_record={"first_name": "Johne", "gender": "male", "dob": "2024-05-02"},
            field_configs=field_configs,
            dataset_a_mapping={"first_name": "first_name", "gender": "gender", "date_of_birth": "dob"},
            dataset_b_mapping={"first_name": "first_name", "gender": "gender", "date_of_birth": "dob"},
        )
        self.assertGreater(result.overall_score, 70.0)
        self.assertEqual(result.band, "Medium")


if __name__ == "__main__":
    unittest.main()
