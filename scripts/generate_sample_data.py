from pathlib import Path

from Levenshtein_Distance.sample_data import write_sample_files


if __name__ == "__main__":
    output_dir = Path("sample_output")
    paths = write_sample_files(output_dir=output_dir, record_count=250, seed=7)
    print(paths["dataset_a_path"])
    print(paths["dataset_b_path"])
