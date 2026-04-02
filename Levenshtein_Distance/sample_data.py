from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any


FIRST_NAMES = [
    "Amina",
    "Chinedu",
    "Fatima",
    "Hassan",
    "Ifeanyi",
    "John",
    "Mariam",
    "Ngozi",
    "Sule",
    "Zainab",
]

LAST_NAMES = [
    "Abdullahi",
    "Adeyemi",
    "Bello",
    "Danjuma",
    "Ibrahim",
    "Johnson",
    "Musa",
    "Nwosu",
    "Okafor",
    "Yakubu",
]

GENDERS = ["Male", "Female"]


def _mutate_name(value: str, index: int) -> str:
    mutations = [
        lambda text: text + "e",
        lambda text: text[:-1] if len(text) > 3 else text,
        lambda text: text.replace("s", "ss").replace("S", "SS"),
        lambda text: text[:-1] + text[-1].lower() if len(text) > 1 else text,
    ]
    return mutations[index % len(mutations)](value)


def _format_dob(value: date, style: str) -> str:
    if style == "dataset_a":
        return value.strftime("%d/%m/%Y")
    return value.strftime("%Y-%m-%d")


def generate_sample_records(record_count: int = 250, seed: int = 7) -> dict[str, list[dict[str, Any]]]:
    random.seed(seed)
    dataset_a_rows: list[dict[str, Any]] = []
    dataset_b_rows: list[dict[str, Any]] = []
    base_date = date(1985, 1, 1)

    for index in range(record_count):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        gender = random.choice(GENDERS)
        phone = f"0803{index:07d}"
        dob = base_date + timedelta(days=random.randint(0, 12000))

        dataset_a_first_name = first_name
        dataset_b_first_name = first_name
        dataset_a_last_name = last_name
        dataset_b_last_name = last_name
        dataset_a_dob = dob
        dataset_b_dob = dob
        dataset_a_gender = gender
        dataset_b_gender = gender

        if index % 8 == 0:
            dataset_b_first_name = _mutate_name(first_name, index)
        if index % 9 == 0:
            dataset_a_last_name = _mutate_name(last_name, index + 1)
        if index % 11 == 0:
            dataset_b_dob = dob.replace(year=max(1950, dob.year - 1))
        elif index % 13 == 0:
            dataset_b_dob = dob.replace(month=1 if dob.month == 12 else dob.month + 1)
        elif index % 17 == 0:
            dataset_b_dob = dob + timedelta(days=1)

        if index % 29 == 0:
            dataset_b_gender = "Female" if gender == "Male" else "Male"

        dataset_a_rows.append(
            {
                "phone_number": phone,
                "given_name": dataset_a_first_name,
                "surname": dataset_a_last_name,
                "date_of_birth": _format_dob(dataset_a_dob, "dataset_a"),
                "sex": dataset_a_gender,
            }
        )
        dataset_b_rows.append(
            {
                "msisdn": phone,
                "first_name": dataset_b_first_name,
                "last_name": dataset_b_last_name,
                "dob": _format_dob(dataset_b_dob, "dataset_b"),
                "gender": dataset_b_gender,
            }
        )

    dataset_a_rows.append(
        {
            "phone_number": "",
            "given_name": "Missing",
            "surname": "Phone",
            "date_of_birth": "03/02/1995",
            "sex": "Male",
        }
    )
    dataset_b_rows.append(
        {
            "msisdn": "",
            "first_name": "Missing",
            "last_name": "Phone",
            "dob": "1995-02-03",
            "gender": "Male",
        }
    )

    if dataset_a_rows:
        duplicate_row = dict(dataset_a_rows[5])
        dataset_a_rows.append(duplicate_row)

    if dataset_b_rows:
        unmatched_row = dict(dataset_b_rows[7])
        unmatched_row["msisdn"] = "09000000000"
        dataset_b_rows.append(unmatched_row)

    if dataset_b_rows:
        invalid_row = dict(dataset_b_rows[15])
        invalid_row["msisdn"] = "08119999999"
        invalid_row["dob"] = "31/31/2020"
        dataset_b_rows.append(invalid_row)

    return {
        "dataset_a": dataset_a_rows,
        "dataset_b": dataset_b_rows,
    }


def write_sample_files(output_dir: Path, record_count: int = 250, seed: int = 7) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    datasets = generate_sample_records(record_count=record_count, seed=seed)

    dataset_a_path = output_dir / "sample_dataset_a.csv"
    dataset_b_path = output_dir / "sample_dataset_b.txt"

    with dataset_a_path.open("w", newline="", encoding="utf-8") as dataset_a_file:
        writer = csv.DictWriter(
            dataset_a_file,
            fieldnames=["phone_number", "given_name", "surname", "date_of_birth", "sex"],
        )
        writer.writeheader()
        writer.writerows(datasets["dataset_a"])

    with dataset_b_path.open("w", newline="", encoding="utf-8") as dataset_b_file:
        writer = csv.DictWriter(
            dataset_b_file,
            fieldnames=["msisdn", "first_name", "last_name", "dob", "gender"],
            delimiter="|",
        )
        writer.writeheader()
        writer.writerows(datasets["dataset_b"])

    return {
        "dataset_a_path": str(dataset_a_path),
        "dataset_b_path": str(dataset_b_path),
    }
