"""Tests des résultats par sous-groupe sur un exemple calculé à la main."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analysis import metrics as m
from src.analysis import subgroups as sg
from src.analysis import validate as v

POP_MOCK = Path("data/mock/population_mock.csv")
SIM_MOCK = Path("data/mock/simulation_results_mock.csv")


def _pop():
    """A, B urbains ; C, D ruraux. Seuils mensuels : urbain 388,92 ; rural 359,33. Poids ménage 10."""
    return pd.DataFrame(
        {
            "household_id": ["A", "B", "C", "D"],
            "household_weight": [10.0] * 4,
            "region": ["r1", "r1", "r2", "r2"],
            "urban_rural": ["urbain", "urbain", "rural", "rural"],
            "household_size": [1, 2, 1, 4],
            "children_count": [0, 1, 0, 2],
            "baseline_consumption": [100.0, 1000.0, 100.0, 1600.0],
            "equivalence_factor": [1.0, 2.0, 1.0, 4.0],
            "equiv_consumption": [100.0, 500.0, 100.0, 400.0],
            "eligible_baseline": [1, 0, 1, 1],
        }
    )


def _sim(pop, monthly_transfer):
    rows = []
    for sc in ["S0", "S1"]:
        for month in range(1, 13):
            for _, r in pop.iterrows():
                tr = 0.0 if sc == "S0" else monthly_transfer.get(r.household_id, 0.0)
                cons = r.equiv_consumption * r.household_size + tr
                rows.append(["R1", sc, 1, month, r.household_id, r.household_weight, 0.0, tr, cons, cons,
                             cons / r.household_size, r.eligible_baseline])
    return pd.DataFrame(rows, columns=v.SIM_COLUMNS)


def _val(df, scenario, dim, value, metric, basis, run="R1"):
    q = (
        (df.run_id == run) & (df.scenario_id == scenario) & (df.subgroup_dimension == dim)
        & (df.subgroup_value == value) & (df.metric == metric) & (df.weighting_basis == basis)
    )
    r = df[q]
    assert len(r) == 1, (scenario, dim, value, metric, basis, len(r))
    return float(r.value.iloc[0])


@pytest.fixture
def case():
    pop = _pop()
    return pop, _sim(pop, {"A": 300.0, "C": 300.0})  # +300 MAD par mois pour A et C (taille 1)


def test_size_group_labels():
    assert sg.size_group(pd.Series([1, 6, 7, 26])).tolist() == ["1", "6", "7+", "7+"]


def test_group_columns_and_values():
    g = sg.add_group_columns(_pop())
    assert g["household_size_group"].tolist() == ["1", "2", "1", "4"]
    assert g["has_children"].tolist() == ["sans enfant", "avec enfants", "sans enfant", "avec enfants"]
    assert g["eligible_baseline"].tolist() == ["éligible", "non éligible", "éligible", "éligible"]


def test_output_format(case):
    pop, sim = case
    out = sg.group_impacts(sim, pop)
    assert list(out.columns) == sg.GROUP_COLUMNS
    assert set(out.subgroup_dimension) == set(sg.DIMENSIONS)
    assert {"population", "R1"} == set(out.run_id)


def test_baseline_headcount_by_hand(case):
    pop, sim = case
    out = sg.group_impacts(sim, pop)
    b = m.BASIS_HOUSEHOLD
    # urbain : A pauvre (100 < 388,92), B non pauvre -> 1/2 ; rural : C pauvre (100 < 359,33), D non (400) -> 1/2
    assert _val(out, "baseline", "urban_rural", "urbain", "poverty_headcount", b, "population") == pytest.approx(0.5)
    assert _val(out, "baseline", "urban_rural", "rural", "poverty_headcount", b, "population") == pytest.approx(0.5)
    # base personne approximée (poids ménage x taille) : urbain 10 / (10 + 20), rural 10 / (10 + 40)
    p = m.BASIS_PERSON_APPROX
    assert _val(out, "baseline", "urban_rural", "urbain", "poverty_headcount", p, "population") == pytest.approx(1 / 3)
    assert _val(out, "baseline", "urban_rural", "rural", "poverty_headcount", p, "population") == pytest.approx(0.2)


def test_scenario_levels_and_changes_by_hand(case):
    pop, sim = case
    out = sg.group_impacts(sim, pop)
    b = m.BASIS_HOUSEHOLD
    # S1 : A passe à 400 (> 388,92) et C à 400 (> 359,33) : plus aucun pauvre
    assert _val(out, "S1", "urban_rural", "urbain", "poverty_headcount", b) == pytest.approx(0.0)
    assert _val(out, "S1", "urban_rural", "urbain", "poverty_headcount_change_vs_S0", b) == pytest.approx(-0.5)
    assert _val(out, "S1", "urban_rural", "rural", "poverty_headcount_change_vs_S0", b) == pytest.approx(-0.5)
    # consommation moyenne urbaine : S0 (100 + 500) / 2 = 300 ; S1 (400 + 500) / 2 = 450
    assert _val(out, "S0", "urban_rural", "urbain", "mean_equiv_consumption", b) == pytest.approx(300.0)
    assert _val(out, "S1", "urban_rural", "urbain", "mean_equiv_consumption", b) == pytest.approx(450.0)
    assert _val(out, "S1", "urban_rural", "urbain", "mean_equiv_consumption_change_vs_S0", b) == pytest.approx(150.0)
    # un groupe sans transfert ne change pas : les ménages B et D (non transférés) restent identiques
    assert _val(out, "S1", "has_children", "avec enfants", "mean_equiv_consumption_change_vs_S0", b) == pytest.approx(0.0)
    assert not out[out.scenario_id == "S0"].metric.str.endswith("_change_vs_S0").any()


def test_group_sizes_weighted_and_unweighted(case):
    pop, sim = case
    out = sg.group_impacts(sim, pop)
    sizes = out[out.metric.str.startswith("group_")]
    assert set(sizes.run_id) == {"population"}

    def get(metric, value, basis):
        r = sizes[(sizes.metric == metric) & (sizes.subgroup_dimension == "urban_rural")
                  & (sizes.subgroup_value == value) & (sizes.weighting_basis == basis)]
        assert len(r) == 1
        return float(r.value.iloc[0])

    assert get("group_households_unweighted", "urbain", sg.BASIS_UNWEIGHTED) == 2
    assert get("group_households_weighted", "urbain", m.BASIS_HOUSEHOLD) == pytest.approx(20.0)
    assert get("group_persons_weighted", "rural", m.BASIS_PERSON_APPROX) == pytest.approx(50.0)  # 10 x 1 + 10 x 4


def test_person_weights_file_is_used(case):
    pop, sim = case
    pw = pd.DataFrame({"household_id": list("ABCD"), "person_weight": [30.0, 10.0, 20.0, 40.0]})
    out = sg.group_impacts(sim, pop, pw)
    assert _val(out, "baseline", "urban_rural", "urbain", "poverty_headcount", m.BASIS_PERSON, "population") == pytest.approx(0.75)
    assert m.BASIS_PERSON_APPROX not in set(out.weighting_basis)


def test_small_groups_are_flagged_not_dropped(case):
    pop, sim = case
    out = sg.group_impacts(sim, pop, min_n=3)  # chaque groupe a moins de 3 ménages : tous signalés
    rows = out[out.subgroup_dimension == "urban_rural"]
    assert rows["notes"].str.contains("effectif faible").all()
    assert len(rows) > 0
    out2 = sg.group_impacts(sim, pop, min_n=2)  # urbain et rural ont 2 ménages : non signalés
    urban = out2[(out2.subgroup_dimension == "urban_rural") & (out2.subgroup_value == "urbain")]
    assert not urban["notes"].str.contains("effectif faible").any()
    single = out2[(out2.subgroup_dimension == "household_size_group") & (out2.subgroup_value == "2")]
    assert single["notes"].str.contains("effectif faible").all()  # un seul ménage de taille 2


def test_unknown_household_raises(case):
    pop, sim = case
    with pytest.raises(ValueError):
        sg.group_impacts(sim, pop.iloc[:3])


@pytest.mark.skipif(not (POP_MOCK.exists() and SIM_MOCK.exists()), reason="mock absente")
def test_mock_group_impacts_are_finite_and_complete():
    pop = pd.read_csv(POP_MOCK, dtype={"household_id": str})
    sim = pd.read_csv(SIM_MOCK, dtype={"household_id": str})
    out = sg.group_impacts(sim, pop)
    assert set(out.subgroup_dimension) == set(sg.DIMENSIONS)
    assert out["value"].notna().all() and np.isfinite(out["value"]).all()
    # toute la mock (20 ménages) est signalée : aucun groupe n'atteint 500 ménages
    assert out["notes"].str.contains("effectif faible").all()


POP_REAL = Path("data/processed/population.csv")
PW_REAL = Path("data/processed/person_weights.csv")


@pytest.mark.skipif(not (POP_REAL.exists() and PW_REAL.exists()), reason="données réelles absentes")
def test_real_baseline_group_rates_match_inspection_report():
    pop = pd.read_csv(POP_REAL, dtype={"household_id": str})
    pw = pd.read_csv(PW_REAL, dtype={"household_id": str})
    out = sg.baseline_group_impacts(pop, pw)

    def rate(dim, value):
        return _val(out, "baseline", dim, value, "poverty_headcount", m.BASIS_PERSON, "population")

    # taux Pauvre par personne du rapport d'inspection (arrondis à 2 décimales en %)
    assert rate("urban_rural", "urbain") == pytest.approx(0.0164, abs=0.0005)
    assert rate("urban_rural", "rural") == pytest.approx(0.0948, abs=0.0005)
    assert rate("region", "Drâa-Tafilalet") == pytest.approx(0.1464, abs=0.0005)
    assert rate("region", "Béni Mellal-Khénifra") == pytest.approx(0.0925, abs=0.0005)
    assert rate("region", "Tanger-Tétouan-Al Hoceïma") == pytest.approx(0.0217, abs=0.0005)
    # les trois petites régions sont signalées, Drâa-Tafilalet (628 ménages) ne l'est pas
    small = out[(out.subgroup_dimension == "region") & out.subgroup_value.isin(
        ["Guelmim-Oued Noun", "Laâyoune-Sakia El Hamra", "Dakhla-Oued Ed Dahab"])]
    assert small["notes"].str.contains("effectif faible").all()
    draa = out[(out.subgroup_dimension == "region") & (out.subgroup_value == "Drâa-Tafilalet")]
    assert not draa["notes"].str.contains("effectif faible").any()
