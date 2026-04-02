import tempfile
import unittest
from pathlib import Path

from Levenshtein_Distance.engine import default_field_configs, parse_delimited_text, process_batch
from Levenshtein_Distance.sample_data import write_sample_files
from Levenshtein_Distance import storage


class PipelineTests(unittest.TestCase):
    def test_process_batch_handles_clean_matches_and_issues(self):
        field_configs = default_field_configs()
        dataset_a_rows = [
            {"phone": "0801", "first_name": "John", "last_name": "Doe", "dob": "2024-04-02", "gender": "Male"},
            {"phone": "0802", "first_name": "Jane", "last_name": "Doe", "dob": "2024-04-02", "gender": "Female"},
            {"phone": "0802", "first_name": "Jane", "last_name": "Doe", "dob": "2024-04-02", "gender": "Female"},
            {"phone": "", "first_name": "Missing", "last_name": "Phone", "dob": "2024-04-02", "gender": "Male"},
        ]
        dataset_b_rows = [
            {"phone": "0801", "first_name": "Johne", "last_name": "Doe", "dob": "2024-04-02", "gender": "Male"},
            {"phone": "0900", "first_name": "No", "last_name": "Match", "dob": "2024-04-02", "gender": "Male"},
        ]
        result = process_batch(
            dataset_a_rows=dataset_a_rows,
            dataset_b_rows=dataset_b_rows,
            field_configs=field_configs,
            dataset_a_mapping={"phone": "phone", "first_name": "first_name", "last_name": "last_name", "date_of_birth": "dob", "gender": "gender"},
            dataset_b_mapping={"phone": "phone", "first_name": "first_name", "last_name": "last_name", "date_of_birth": "dob", "gender": "gender"},
            dataset_a_phone_column="phone",
            dataset_b_phone_column="phone",
        )
        self.assertEqual(result["summary"]["matched_count"], 1)
        issue_types = {issue["issue_type"] for issue in result["issues"]}
        self.assertIn("missing_phone", issue_types)
        self.assertIn("duplicate_phone", issue_types)
        self.assertIn("unmatched_phone", issue_types)

    def test_sample_generator_writes_parseable_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_sample_files(Path(temp_dir), record_count=30, seed=11)
            dataset_a = parse_delimited_text(Path(paths["dataset_a_path"]).read_bytes(), "sample_dataset_a.csv")
            dataset_b = parse_delimited_text(Path(paths["dataset_b_path"]).read_bytes(), "sample_dataset_b.txt")
            self.assertGreater(len(dataset_a["rows"]), 20)
            self.assertGreater(len(dataset_b["rows"]), 20)
            self.assertIn("phone_number", dataset_a["headers"])
            self.assertIn("msisdn", dataset_b["headers"])

    def test_storage_round_trip_with_status_update(self):
        original_path = storage.DATABASE_PATH
        temp_path = Path(tempfile.gettempdir()) / "levenshtein_distance_storage_test.db"
        if temp_path.exists():
            temp_path.unlink()
        try:
            storage.DATABASE_PATH = temp_path
            storage.initialize_database()
            run_id = storage.create_run(
                dataset_a_filename="l.csv",
                dataset_b_filename="n.csv",
                dataset_a_mapping={"phone": "phone"},
                dataset_b_mapping={"phone": "phone"},
                results=[
                    {
                        "phone_key": "0801",
                        "overall_score": 95.0,
                        "band": "High",
                        "breakdowns": [],
                        "dataset_a_record": {"phone": "0801"},
                        "dataset_b_record": {"phone": "0801"},
                    }
                ],
                issues=[],
                summary={"matched_count": 1, "issue_count": 0, "high_count": 1, "medium_count": 0, "low_count": 0},
            )
            runs = storage.list_runs()
            self.assertEqual(runs[0]["id"], run_id)
            results = storage.get_run_results(run_id)
            self.assertEqual(results[0]["reviewer_status"], "Pending")
            storage.update_result_review(results[0]["id"], "Confirmed", "Looks valid")
            updated_result = storage.get_result(results[0]["id"])
            self.assertEqual(updated_result["reviewer_status"], "Confirmed")
            self.assertEqual(updated_result["reviewer_note"], "Looks valid")
        finally:
            storage.DATABASE_PATH = original_path
            if temp_path.exists():
                temp_path.unlink()


if __name__ == "__main__":
    unittest.main()
