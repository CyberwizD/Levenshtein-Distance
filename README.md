# Levenshtein-Distance Algorithm

Reflex + SQLite prototype for comparing user records using levenshtein distance algorithm.

## What it does

- Upload `.csv` or header-based `.txt` files
- Map each dataset's columns to scoring fields
- Score matched pairs with configurable field weights
- Use normalized Levenshtein similarity for text fields
- Split DOB scoring into year `50%`, month `25%`, and day `25%`
- Persist comparison runs, ranked results, issues, and reviewer decisions in SQLite
- Support manual side-by-side comparison for quick checks
- Generate local sample datasets for demo/testing

## Default scoring

- `first_name`: `30`
- `last_name`: `30`
- `date_of_birth`: `20`
- `gender`: `20`

Active field weights must total exactly `100` before a batch or manual run can execute.

## Run locally

```bash
reflex run
```

## Generate sample data

```bash
.\venv\Scripts\python.exe scripts\generate_sample_data.py
```

## Tests

```bash
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```
