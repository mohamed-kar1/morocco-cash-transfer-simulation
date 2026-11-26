"""Tests des indicateurs sur de petits exemples calculés à la main (guide, section 8)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analysis import metrics as m
from src.analysis import validate as v

POP_MOCK = Path("data/mock/population_mock.csv")
SIM_MOCK = Path("data/mock/simulation_results_mock.csv")
POP_REAL = Path("data/processed/population.csv")
PW_REAL = Path("data/processed/person_weights.csv")


# ----------------------------------------------------------------------------- primitives


def test_weighted_mean():
    assert m.weighted_mean([10, 20], [1, 3]) == pytest.approx(17.5)


def test_headcount_is_strict_and_weighted():
    # seuil 100 ; 50 est pauvre, 100 ne l'est pas ; poids 1, 1, 2 -> 1/4
    assert m.poverty_headcount([50, 100, 150], 100, [1, 1, 2]) == pytest.approx(0.25)


def test_poverty_gap_index_and_total():
    # écart du premier ménage : (100 - 50) / 100 = 0,5 ; poids 1 sur 4 -> 0,125
    assert m.poverty_gap([50, 100, 150], 100, [1, 1, 2]) == pytest.approx(0.125)
    assert m.poverty_gap_total([50, 100, 150], 100, [1, 1, 2]) == pytest.approx(50.0)


def test_line_can_differ_by_household():
    # ménage 1 : seuil 60 (50 pauvre) ; ménage 2 : seuil 40 (50 non pauvre)
    assert m.poverty_headcount([50, 50], [60, 40], [1, 1]) == pytest.approx(0.5)


def test_gini_hand_computed():
    assert m.gini([1, 2, 3, 4], [1, 1, 1, 1]) == pytest.approx(0.25)
    # équivaut à la population [1, 3, 3, 3]
    assert m.gini([1, 3], [1, 3]) == pytest.approx(0.15)
    assert m.gini([5, 5, 5], [1, 2, 3]) == pytest.approx(0.0)


def test_gini_ignores_input_order():
    assert m.gini([4, 1, 3, 2], [1, 1, 1, 1]) == pytest.approx(0.25)


def test_zero_denominators_return_nan_not_inf():
    assert np.isnan(m.weighted_mean([1, 2], [0, 0]))
    assert np.isnan(m.poverty_headcount([1, 2], 10, [0, 0]))
    assert np.isnan(m.poverty_gap([1, 2], 10, [0, 0]))
    assert np.isnan(m.gini([0, 0], [1, 1]))


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        m.weighted_mean([1, np.nan], [1, 1])
    with pytest.raises(ValueError):
        m.weighted_mean([1, 2], [1, -1])
    with pytest.raises(ValueError):
        m.weighted_mean([1, 2, 3], [1, 1])
    with pytest.raises(ValueError):
        m.gini([-1, 2], [1, 1])
    with pytest.raises(ValueError):
        m.poverty_gap([1, 2], 0, [1, 1])


# ----------------------------------------------------------------------------- niveaux et écarts


@pytest.fixture
def tiny():
    pop = pd.DataFrame(
        {
            "household_id": ["A", "B"],
            "household_weight": [100.0, 100.0],
            "region": ["r1", "r1"],
            "urban_rural": ["urbain", "rural"],
            "household_size": [2, 4],
            "children_count": [0, 2],
            "baseline_consumption": [600.0, 1000.0],
            "equivalence_factor": [2.0, 4.0],
            "equiv_consumption": [300.0, 250.0],  # sous 388,92 (urbain) et sous 359,33 (rural)
            "eligible_baseline": [1, 1],
        }
    )
    rows = []
    for scenario, bonus in [("S0", 0.0), ("S1", 100.0)]:
        for month in range(1, 13):
            for hid, size, equiv in [("A", 2, 300.0), ("B", 4, 250.0)]:
                transfer = bonus if scenario != "S0" else 0.0
                cons = equiv * size + transfer
                rows.append(
                    ["R1", scenario, 42, month, hid, 100.0, 0.0, transfer, cons, cons, cons / size, 1]
                )
    sim = pd.DataFrame(rows, columns=v.SIM_COLUMNS)
    return pop, sim


def _value(df, scenario, metric, basis):
    r = df[(df.scenario_id == scenario) & (df.metric == metric) & (df.weighting_basis == basis)]
    assert len(r) == 1
    return float(r.value.iloc[0])


def test_baseline_metrics_tiny(tiny):
    pop, _ = tiny
    out = m.baseline_metrics(pop)
    assert list(out.columns) == m.LONG_COLUMNS
    assert _value(out, "baseline", "poverty_headcount", m.BASIS_HOUSEHOLD) == pytest.approx(1.0)
    # écart : A (388,9167 - 300) / 388,9167 ; B (359,3333 - 250) / 359,3333 ; poids égaux
    gap = ((4667 / 12 - 300) / (4667 / 12) + (4312 / 12 - 250) / (4312 / 12)) / 2
    assert _value(out, "baseline", "poverty_gap", m.BASIS_HOUSEHOLD) == pytest.approx(gap)
    assert _value(out, "baseline", "mean_equiv_consumption", m.BASIS_HOUSEHOLD) == pytest.approx(275.0)
    # base personne approximée : poids 200 et 400
    assert _value(out, "baseline", "mean_equiv_consumption", m.BASIS_PERSON_APPROX) == pytest.approx(
        (300 * 200 + 250 * 400) / 600
    )


def test_person_weights_file_replaces_approximation(tiny):
    pop, _ = tiny
    pw = pd.DataFrame({"household_id": ["A", "B"], "person_weight": [30.0, 10.0]})
    out = m.baseline_metrics(pop, pw)
    assert _value(out, "baseline", "mean_equiv_consumption", m.BASIS_PERSON) == pytest.approx(
        (300 * 30 + 250 * 10) / 40
    )
    with pytest.raises(ValueError):
        m.baseline_metrics(pop, pw.iloc[:1])


def test_scenario_metrics_levels_and_changes(tiny):
    pop, sim = tiny
    out = m.scenario_metrics(sim, pop)
    # S1 ajoute 100 MAD de consommation par mois ; équivalent : +50 (A) et +25 (B)
    assert _value(out, "S0", "mean_equiv_consumption", m.BASIS_HOUSEHOLD) == pytest.approx(275.0)
    assert _value(out, "S1", "mean_equiv_consumption", m.BASIS_HOUSEHOLD) == pytest.approx(312.5)
    assert _value(out, "S1", "mean_equiv_consumption_change_vs_S0", m.BASIS_HOUSEHOLD) == pytest.approx(37.5)
    # après transfert, A = 350 (< 388,9) et B = 275 (< 359,3) : toujours pauvres
    assert _value(out, "S1", "poverty_headcount", m.BASIS_HOUSEHOLD) == pytest.approx(1.0)
    assert _value(out, "S1", "poverty_gap_change_vs_S0", m.BASIS_HOUSEHOLD) < 0
    assert not (out[out.scenario_id == "S0"].metric.str.endswith("_change_vs_S0")).any()


def test_scenario_metrics_rejects_unknown_household(tiny):
    pop, sim = tiny
    with pytest.raises(ValueError):
        m.scenario_metrics(sim, pop.iloc[:1])


# ----------------------------------------------------------------------------- validation B1


def test_validate_accepts_consistent_input(tiny):
    pop, sim = tiny
    v.validate_simulation_results(sim, pop)


def test_validate_rejects_duplicates_and_bad_units(tiny):
    pop, sim = tiny
    with pytest.raises(ValueError, match="doublon"):
        v.validate_simulation_results(pd.concat([sim, sim.iloc[:1]]), pop)
    annual = sim.copy()
    annual["equiv_consumption_outcome"] *= 12  # montants annuels au lieu de mensuels
    with pytest.raises(ValueError, match="unités"):
        v.validate_simulation_results(annual, pop)
    bad_s0 = sim.copy()
    bad_s0.loc[bad_s0.scenario_id == "S0", "transfer_amount"] = 1.0
    with pytest.raises(ValueError, match="S0"):
        v.validate_simulation_results(bad_s0, pop)


def test_validate_rejects_missing_months_and_columns(tiny):
    pop, sim = tiny
    with pytest.raises(ValueError, match="mois"):
        v.validate_simulation_results(sim[sim.month != 12], pop)
    with pytest.raises(ValueError, match="colonnes"):
        v.validate_simulation_results(sim.drop(columns=["seed"]), pop)


# ----------------------------------------------------------------------------- fixture fictive et données réelles


@pytest.mark.skipif(not (POP_MOCK.exists() and SIM_MOCK.exists()), reason="mock absente")
def test_mock_simulation_passes_validation_and_metrics_are_finite():
    pop = pd.read_csv(POP_MOCK, dtype={"household_id": str})
    sim = pd.read_csv(SIM_MOCK, dtype={"household_id": str})
    v.validate_simulation_results(sim, pop)
    out = m.scenario_metrics(sim, pop)
    assert set(out.scenario_id) == {"S0", "S1", "S2", "S3"}
    assert out["value"].notna().all()
    assert np.isfinite(out["value"]).all()
    # mêmes chocs, plus de transferts : la consommation moyenne ne baisse pas par rapport à S0
    chg = out[(out.metric == "mean_equiv_consumption_change_vs_S0") & (out.weighting_basis == m.BASIS_HOUSEHOLD)]
    assert (chg["value"] >= -1e-9).all()


@pytest.mark.skipif(not (POP_REAL.exists() and PW_REAL.exists()), reason="données réelles absentes")
def test_real_baseline_reproduces_hcp_rates():
    pop = pd.read_csv(POP_REAL, dtype={"household_id": str})
    pw = pd.read_csv(PW_REAL, dtype={"household_id": str})
    out = m.baseline_metrics(pop, pw)
    assert _value(out, "baseline", "poverty_headcount", m.BASIS_PERSON) == pytest.approx(0.0478, abs=0.0005)  # HCP : 4,8 %
    assert _value(out, "baseline", "poverty_headcount", m.BASIS_HOUSEHOLD) == pytest.approx(0.0300, abs=0.0005)
    urban = pop[pop.urban_rural == "urbain"].reset_index(drop=True)
    rural = pop[pop.urban_rural == "rural"].reset_index(drop=True)
    assert _value(m.baseline_metrics(urban, pw), "baseline", "poverty_headcount", m.BASIS_PERSON) == pytest.approx(0.0164, abs=0.0005)
    assert _value(m.baseline_metrics(rural, pw), "baseline", "poverty_headcount", m.BASIS_PERSON) == pytest.approx(0.0948, abs=0.0005)
