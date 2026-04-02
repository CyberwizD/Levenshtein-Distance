from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


TEXT_SIMILARITY = "text_similarity"
EXACT_MATCH = "exact_match"
DATE_PARTS = "date_parts"

DATE_WEIGHT_SPLIT = {
    "year": 0.5,
    "month": 0.25,
    "day": 0.25,
}

SUPPORTED_DELIMITERS = [",", "\t", "|"]
DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%d %b %Y",
    "%d %B %Y",
)


@dataclass
class FieldConfig:
    key: str
    label: str
    comparator: str
    weight: float
    active: bool = True


@dataclass
class FieldBreakdown:
    key: str
    label: str
    comparator: str
    left_value: str
    right_value: str
    matched: bool
    similarity: float
    score: float
    max_score: float
    details: list[str]


@dataclass
class ComparisonResult:
    phone_key: str
    overall_score: float
    band: str
    breakdowns: list[FieldBreakdown]
    dataset_a_record: dict[str, str]
    dataset_b_record: dict[str, str]


@dataclass
class ComparisonIssue:
    phone_key: str
    issue_type: str
    source_context: str
    details: dict[str, Any]


def default_field_configs() -> list[dict[str, Any]]:
    return [
        {
            "key": "first_name",
            "label": "First Name",
            "comparator": TEXT_SIMILARITY,
            "weight": 30.0,
            "active": True,
        },
        {
            "key": "last_name",
            "label": "Last Name",
            "comparator": TEXT_SIMILARITY,
            "weight": 30.0,
            "active": True,
        },
        {
            "key": "date_of_birth",
            "label": "Date of Birth",
            "comparator": DATE_PARTS,
            "weight": 20.0,
            "active": True,
        },
        {
            "key": "gender",
            "label": "Gender",
            "comparator": EXACT_MATCH,
            "weight": 20.0,
            "active": True,
        },
    ]


def field_configs_from_dicts(field_configs: list[dict[str, Any]]) -> list[FieldConfig]:
    return [FieldConfig(**field_config) for field_config in field_configs if field_config.get("active", True)]


def active_weight_total(field_configs: list[dict[str, Any]]) -> float:
    total = 0.0
    for field_config in field_configs:
        if field_config.get("active", True):
            total += float(field_config.get("weight", 0) or 0)
    return round(total, 2)


def detect_delimiter(sample_text: str) -> str:
    lines = [line for line in sample_text.splitlines()[:5] if line.strip()]
    if not lines:
        return ","

    delimiter_scores = {
        delimiter: sum(line.count(delimiter) for line in lines)
        for delimiter in SUPPORTED_DELIMITERS
    }
    best_delimiter = max(delimiter_scores, key=delimiter_scores.get)
    if delimiter_scores[best_delimiter] == 0:
        return ","
    return best_delimiter


def decode_file_bytes(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def parse_delimited_text(content: bytes, filename: str) -> dict[str, Any]:
    text = decode_file_bytes(content)
    delimiter = detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    headers = [header.strip() for header in (reader.fieldnames or []) if header and header.strip()]
    rows: list[dict[str, str]] = []

    for row in reader:
        cleaned_row = {
            header: str(row.get(header, "") or "").strip()
            for header in headers
        }
        if any(value for value in cleaned_row.values()):
            rows.append(cleaned_row)

    return {
        "filename": Path(filename).name,
        "delimiter": delimiter,
        "headers": headers,
        "rows": rows,
    }


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_phone(value: Any) -> str:
    return str(value or "").strip()


def levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous_row = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current_row = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            insertion_cost = current_row[right_index - 1] + 1
            deletion_cost = previous_row[right_index] + 1
            substitution_cost = previous_row[right_index - 1] + (left_char != right_char)
            current_row.append(min(insertion_cost, deletion_cost, substitution_cost))
        previous_row = current_row
    return previous_row[-1]


def text_similarity(left_value: Any, right_value: Any) -> float:
    left = normalize_text(left_value)
    right = normalize_text(right_value)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    distance = levenshtein_distance(left, right)
    longest = max(len(left), len(right))
    return max(0.0, 1.0 - (distance / longest))


def parse_date(value: Any) -> tuple[datetime | None, str | None]:
    raw_value = str(value or "").strip()
    if not raw_value:
        return None, "missing"

    normalized = re.sub(r"\s+", " ", raw_value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(normalized, fmt), None
        except ValueError:
            continue
    return None, f"invalid date: {raw_value}"


def score_text_field(field_config: FieldConfig, left_value: Any, right_value: Any) -> FieldBreakdown:
    similarity = text_similarity(left_value, right_value)
    score = round(field_config.weight * similarity, 2)
    details: list[str] = []
    if similarity == 1.0:
        details.append("Exact match after trim/lowercase normalization.")
    elif similarity == 0.0:
        details.append("No text similarity after trim/lowercase normalization.")
    else:
        details.append(f"Levenshtein similarity: {round(similarity * 100, 2)}%.")

    return FieldBreakdown(
        key=field_config.key,
        label=field_config.label,
        comparator=field_config.comparator,
        left_value=str(left_value or ""),
        right_value=str(right_value or ""),
        matched=similarity == 1.0,
        similarity=round(similarity, 4),
        score=score,
        max_score=field_config.weight,
        details=details,
    )


def score_exact_field(field_config: FieldConfig, left_value: Any, right_value: Any) -> FieldBreakdown:
    matched = normalize_text(left_value) == normalize_text(right_value)
    score = round(field_config.weight if matched else 0.0, 2)
    details = ["Exact normalized match."] if matched else ["Exact normalized mismatch."]
    return FieldBreakdown(
        key=field_config.key,
        label=field_config.label,
        comparator=field_config.comparator,
        left_value=str(left_value or ""),
        right_value=str(right_value or ""),
        matched=matched,
        similarity=1.0 if matched else 0.0,
        score=score,
        max_score=field_config.weight,
        details=details,
    )


def score_date_field(field_config: FieldConfig, left_value: Any, right_value: Any) -> FieldBreakdown:
    left_date, left_error = parse_date(left_value)
    right_date, right_error = parse_date(right_value)
    details: list[str] = []

    if left_error or right_error:
        if left_error:
            details.append(f"Dataset A DOB {left_error}.")
        if right_error:
            details.append(f"Dataset B DOB {right_error}.")
        return FieldBreakdown(
            key=field_config.key,
            label=field_config.label,
            comparator=field_config.comparator,
            left_value=str(left_value or ""),
            right_value=str(right_value or ""),
            matched=False,
            similarity=0.0,
            score=0.0,
            max_score=field_config.weight,
            details=details,
        )

    awarded = 0.0
    comparisons = {
        "year": left_date.year == right_date.year,
        "month": left_date.month == right_date.month,
        "day": left_date.day == right_date.day,
    }
    for part_name, matched in comparisons.items():
        part_weight = field_config.weight * DATE_WEIGHT_SPLIT[part_name]
        if matched:
            awarded += part_weight
            details.append(f"{part_name.title()} matches.")
        else:
            details.append(f"{part_name.title()} mismatch.")

    score = round(awarded, 2)
    similarity = round(score / field_config.weight, 4) if field_config.weight else 0.0
    return FieldBreakdown(
        key=field_config.key,
        label=field_config.label,
        comparator=field_config.comparator,
        left_value=str(left_value or ""),
        right_value=str(right_value or ""),
        matched=all(comparisons.values()),
        similarity=similarity,
        score=score,
        max_score=field_config.weight,
        details=details,
    )


def score_field(field_config: FieldConfig, left_value: Any, right_value: Any) -> FieldBreakdown:
    if field_config.comparator == TEXT_SIMILARITY:
        return score_text_field(field_config, left_value, right_value)
    if field_config.comparator == EXACT_MATCH:
        return score_exact_field(field_config, left_value, right_value)
    if field_config.comparator == DATE_PARTS:
        return score_date_field(field_config, left_value, right_value)
    raise ValueError(f"Unsupported comparator: {field_config.comparator}")


def score_band(score: float) -> str:
    if score >= 90:
        return "High"
    if score >= 70:
        return "Medium"
    return "Low"


def compare_records(
    phone_key: str,
    dataset_a_record: dict[str, str],
    dataset_b_record: dict[str, str],
    field_configs: list[dict[str, Any]],
    dataset_a_mapping: dict[str, str],
    dataset_b_mapping: dict[str, str],
) -> ComparisonResult:
    active_configs = field_configs_from_dicts(field_configs)
    breakdowns: list[FieldBreakdown] = []

    for field_config in active_configs:
        dataset_a_value = dataset_a_record.get(dataset_a_mapping.get(field_config.key, ""), "")
        dataset_b_value = dataset_b_record.get(dataset_b_mapping.get(field_config.key, ""), "")
        breakdowns.append(score_field(field_config, dataset_a_value, dataset_b_value))

    overall_score = round(sum(item.score for item in breakdowns), 2)
    return ComparisonResult(
        phone_key=phone_key,
        overall_score=overall_score,
        band=score_band(overall_score),
        breakdowns=breakdowns,
        dataset_a_record=dataset_a_record,
        dataset_b_record=dataset_b_record,
    )


def _build_issue(phone_key: str, issue_type: str, source_context: str, details: dict[str, Any]) -> dict[str, Any]:
    return asdict(ComparisonIssue(phone_key=phone_key, issue_type=issue_type, source_context=source_context, details=details))


def _index_rows(rows: list[dict[str, str]], phone_column: str, source_name: str) -> tuple[dict[str, list[dict[str, str]]], list[dict[str, Any]]]:
    indexed_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    issues: list[dict[str, Any]] = []

    for row_number, row in enumerate(rows, start=1):
        phone_key = normalize_phone(row.get(phone_column, ""))
        if not phone_key:
            issues.append(
                _build_issue(
                    phone_key="",
                    issue_type="missing_phone",
                    source_context=source_name,
                    details={
                        "row_number": row_number,
                        "record": row,
                    },
                )
            )
            continue
        indexed_rows[phone_key].append(row)

    return indexed_rows, issues


def process_batch(
    dataset_a_rows: list[dict[str, str]],
    dataset_b_rows: list[dict[str, str]],
    field_configs: list[dict[str, Any]],
    dataset_a_mapping: dict[str, str],
    dataset_b_mapping: dict[str, str],
    dataset_a_phone_column: str,
    dataset_b_phone_column: str,
) -> dict[str, Any]:
    dataset_a_index, dataset_a_issues = _index_rows(dataset_a_rows, dataset_a_phone_column, "dataset_a")
    dataset_b_index, dataset_b_issues = _index_rows(dataset_b_rows, dataset_b_phone_column, "dataset_b")

    issues = [*dataset_a_issues, *dataset_b_issues]
    results: list[dict[str, Any]] = []

    all_phone_keys = set(dataset_a_index) | set(dataset_b_index)
    for phone_key in sorted(all_phone_keys):
        dataset_a_matches = dataset_a_index.get(phone_key, [])
        dataset_b_matches = dataset_b_index.get(phone_key, [])

        if len(dataset_a_matches) > 1 or len(dataset_b_matches) > 1:
            issues.append(
                _build_issue(
                    phone_key=phone_key,
                    issue_type="duplicate_phone",
                    source_context="join",
                    details={
                        "dataset_a_count": len(dataset_a_matches),
                        "dataset_b_count": len(dataset_b_matches),
                    },
                )
            )
            continue

        if not dataset_a_matches or not dataset_b_matches:
            issues.append(
                _build_issue(
                    phone_key=phone_key,
                    issue_type="unmatched_phone",
                    source_context="join",
                    details={
                        "dataset_a_count": len(dataset_a_matches),
                        "dataset_b_count": len(dataset_b_matches),
                    },
                )
            )
            continue

        comparison = compare_records(
            phone_key=phone_key,
            dataset_a_record=dataset_a_matches[0],
            dataset_b_record=dataset_b_matches[0],
            field_configs=field_configs,
            dataset_a_mapping=dataset_a_mapping,
            dataset_b_mapping=dataset_b_mapping,
        )
        result_dict = asdict(comparison)
        results.append(result_dict)

        for breakdown in result_dict["breakdowns"]:
            has_invalid_detail = any("invalid date" in detail.lower() for detail in breakdown["details"])
            if has_invalid_detail:
                issues.append(
                    _build_issue(
                        phone_key=phone_key,
                        issue_type="invalid_value",
                        source_context=breakdown["key"],
                        details={
                            "field": breakdown["label"],
                            "left_value": breakdown["left_value"],
                            "right_value": breakdown["right_value"],
                            "messages": breakdown["details"],
                        },
                    )
                )

    results.sort(key=lambda item: item["overall_score"], reverse=True)
    high_count = len([item for item in results if item["band"] == "High"])
    medium_count = len([item for item in results if item["band"] == "Medium"])
    low_count = len([item for item in results if item["band"] == "Low"])

    return {
        "results": results,
        "issues": issues,
        "summary": {
            "matched_count": len(results),
            "issue_count": len(issues),
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
        },
    }
