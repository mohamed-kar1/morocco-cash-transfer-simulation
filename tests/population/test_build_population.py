from pathlib import Path

import pandas as pd
import pytest

from src.population import build_population as b

MOCK = Path("data/mock/population_mock.csv")
OUT = Path("data/processed/population.csv")


@pytest.fixture
def raw():
    menage = pd.DataFrame(
        {
            "N_ménage": [1.0, 2.0, 3.0],
            "coef_ménage": [100.5, 200.0, 50.0],
            "Milieu": [1.0, 2.0, 1.0],
            "Région_12": [1.0, 2.0, 1.0],
            "Taille_ménage": [" 4", "1", "2"],
            "Pauvre": [1.0, 0.0, 0.0],
            "Vulnérable": [0.0, 0.0, 1.0],
            "DAM": [12000.0, 24000.0, 36000.0],
        }
    )
    # ménage 1 : 2 enfants + 2 adultes ; ménage 2 : 1 adulte ; ménage 3 : 1 enfant de 14 ans + 1 adulte
    indiv = pd.DataFrame(
        {
            "N_ménage": [1, 1, 1, 1, 2, 3, 3],
            "Age": [3, 14, 15, 40, 60, 14, 35],
        }
    )
    return menage, indiv, {1.0: "Casablanca-Settat", 2.0: "Oriental"}


def test_build_columns_and_contract(raw):
    pop = b.build_population(*raw)
    assert list(pop.columns) == b.COLUMNS
    b.validate_contract(pop)


def test_household_id_is_text(raw):
    pop = b.build_population(*raw)
    assert pop["household_id"].tolist() == ["1", "2", "3"]


def test_children_under_15(raw):
    pop = b.build_population(*raw)
    assert pop["children_count"].tolist() == [2, 0, 1]  # 15 ans n'est pas un enfant


def test_formulas_and_eligibility(raw):
    pop = b.build_population(*raw)
    assert pop["baseline_consumption"].tolist() == [1000.0, 2000.0, 3000.0]
    assert pop["equivalence_factor"].tolist() == [4.0, 1.0, 2.0]
    assert pop["equiv_consumption"].tolist() == [250.0, 2000.0, 1500.0]
    assert pop["eligible_baseline"].tolist() == [1, 0, 1]
    assert pop["urban_rural"].tolist() == ["urbain", "rural", "urbain"]
    assert pop["region"].tolist() == ["Casablanca-Settat", "Oriental", "Casablanca-Settat"]


def test_build_log_records_row_counts(raw, tmp_path):
    log = b.BuildLog()
    pop = b.build_population(*raw, log=log)
    assert len(log.steps) >= 4
    assert all(st["exclues"] == 0 for st in log.steps)
    assert log.steps[-1]["apres"] == len(pop)
    out = tmp_path / "log.md"
    log.write(out, {"Lignes": len(pop)})
    text = out.read_text(encoding="utf-8")
    assert "Journal de construction" in text and "Lignes avant" in text


def test_build_without_log_still_works(raw):
    assert len(b.build_population(*raw)) == 3


def test_household_without_individuals_gets_zero_children(raw):
    menage, indiv, labels = raw
    pop = b.build_population(menage, indiv[indiv["N_ménage"] != 2], labels)
    assert pop.loc[1, "children_count"] == 0


def test_unknown_milieu_code_raises(raw):
    menage, indiv, labels = raw
    menage.loc[0, "Milieu"] = 9
    with pytest.raises(ValueError):
        b.build_population(menage, indiv, labels)


def test_contract_rejects_children_above_size(raw):
    pop = b.build_population(*raw)
    pop.loc[1, "children_count"] = 5
    with pytest.raises(ValueError):
        b.validate_contract(pop)


@pytest.mark.skipif(not MOCK.exists(), reason="mock absente")
def test_columns_match_mock_and_mock_passes_contract():
    mock = pd.read_csv(MOCK)
    assert list(mock.columns) == b.COLUMNS
    b.validate_contract(mock)


@pytest.mark.skipif(not OUT.exists(), reason="population.csv pas encore construit")
def test_real_population_matches_survey_totals():
    pop = pd.read_csv(OUT)
    b.validate_contract(pop)
    assert len(pop) == b.EXPECTED_ROWS
    assert abs(pop["household_weight"].sum() - b.EXPECTED_WEIGHT_SUM) <= 1
    assert int(pop["eligible_baseline"].sum()) == b.EXPECTED_ELIGIBLE
    assert pop["region"].nunique() == 12


def _menage_with_person_weights():
    return pd.DataFrame(
        {"N_ménage": [1.0, 2.0, 3.0], "coef_indiv": [400.0, 150.5, 90.0]}
    )


def test_person_weights_match_population_ids(raw):
    menage, indiv, labels = raw
    menage = menage.assign(coef_indiv=[400.0, 150.5, 90.0])
    pop = b.build_population(menage, indiv, labels)
    pw = b.build_person_weights(menage)
    assert list(pw.columns) == ["household_id", "person_weight"]
    assert pw["household_id"].tolist() == pop["household_id"].tolist()
    assert pw["person_weight"].tolist() == [400.0, 150.5, 90.0]
    b.validate_person_weights(pw, pop)


def test_person_weights_reject_non_positive(raw):
    menage, indiv, labels = raw
    menage = menage.assign(coef_indiv=[400.0, 0.0, 90.0])
    pop = b.build_population(menage, indiv, labels)
    with pytest.raises(ValueError):
        b.validate_person_weights(b.build_person_weights(menage), pop)


@pytest.mark.skipif(not b.PERSON_WEIGHTS_CSV.exists(), reason="person_weights.csv pas encore construit")
def test_real_person_weights_sum():
    pw = pd.read_csv(b.PERSON_WEIGHTS_CSV, dtype={"household_id": str})
    assert len(pw) == b.EXPECTED_ROWS
    assert abs(pw["person_weight"].sum() - b.EXPECTED_PERSON_WEIGHT_SUM) <= 1
