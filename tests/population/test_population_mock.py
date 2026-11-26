import csv
from pathlib import Path

MOCK = Path("data/mock/population_mock.csv")
COLUMNS = [
    "household_id", "household_weight", "region", "urban_rural", "household_size",
    "children_count", "baseline_consumption", "equivalence_factor",
    "equiv_consumption", "eligible_baseline",
]


def _rows():
    with MOCK.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_columns_match_contract():
    with MOCK.open(encoding="utf-8", newline="") as f:
        assert next(csv.reader(f)) == COLUMNS


def test_ids_unique_and_values_valid():
    rows = _rows()
    assert len({r["household_id"] for r in rows}) == len(rows)
    for r in rows:
        size = int(r["household_size"])
        assert size >= 1 and 0 <= int(r["children_count"]) <= size
        assert float(r["household_weight"]) > 0
        assert r["urban_rural"] in {"urbain", "rural"}
        assert r["eligible_baseline"] in {"0", "1"}


def test_equiv_consumption_formula():
    for r in _rows():
        expected = float(r["baseline_consumption"]) / float(r["equivalence_factor"])
        assert abs(float(r["equiv_consumption"]) - expected) < 0.01
