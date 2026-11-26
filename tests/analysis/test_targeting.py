"""Tests du ciblage, du coût et du coût-efficacité sur un exemple calculé à la main."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analysis import metrics as m
from src.analysis import targeting as t
from src.analysis import validate as v

POP_MOCK = Path("data/mock/population_mock.csv")
SIM_MOCK = Path("data/mock/simulation_results_mock.csv")


def _pop():
    """4 ménages urbains de taille 1, poids 10 ; seuil mensuel urbain = 4667 / 12 = 388,92.

    A (100) et B (200) sont pauvres ; C (500) et D (600) ne le sont pas. Éligibles : A, B, C.
    """
    return pd.DataFrame(
        {
            "household_id": ["A", "B", "C", "D"],
            "household_weight": [10.0] * 4,
            "region": ["r"] * 4,
            "urban_rural": ["urbain"] * 4,
            "household_size": [1] * 4,
            "children_count": [0] * 4,
            "baseline_consumption": [100.0, 200.0, 500.0, 600.0],
            "equivalence_factor": [1.0] * 4,
            "equiv_consumption": [100.0, 200.0, 500.0, 600.0],
            "eligible_baseline": [1, 1, 1, 0],
        }
    )


def _sim(pop, monthly_transfer: dict, scenario="S1", run_id="R1", extra_s0=True):
    """S0 sans transfert, puis un scénario où chaque transfert mensuel s'ajoute à la consommation (réponse = 1)."""
    rows = []
    scenarios = (["S0"] if extra_s0 else []) + [scenario]
    for sc in scenarios:
        for month in range(1, 13):
            for _, r in pop.iterrows():
                transfer = 0.0 if sc == "S0" else monthly_transfer.get(r.household_id, 0.0)
                cons = r.equiv_consumption * r.household_size + transfer
                rows.append(
                    [run_id, sc, 1, month, r.household_id, r.household_weight, 0.0, transfer, cons, cons,
                     cons / r.household_size, r.eligible_baseline]
                )
    return pd.DataFrame(rows, columns=v.SIM_COLUMNS)


def _val(df, scenario, metric, basis=None):
    q = (df.scenario_id == scenario) & (df.metric == metric)
    if basis is not None:
        q &= df.weighting_basis == basis
    r = df[q]
    assert len(r) == 1, (metric, basis, len(r))
    return float(r.value.iloc[0])


@pytest.fixture
def case():
    pop = _pop()
    sim = _sim(pop, {"A": 50.0, "C": 50.0})  # A (pauvre) et C (non pauvre) reçoivent 50 MAD par mois
    return pop, sim


def test_output_format_and_no_s0_rows(case):
    pop, sim = case
    out = t.scenario_targeting_and_cost(sim, pop)
    assert list(out.columns) == m.LONG_COLUMNS
    assert set(out.scenario_id) == {"S1"}


def test_targeting_household_basis_by_hand(case):
    pop, sim = case
    out = t.scenario_targeting_and_cost(sim, pop)
    b = m.BASIS_HOUSEHOLD
    assert _val(out, "S1", "coverage_eligible", b) == pytest.approx(2 / 3)  # A et C parmi A, B, C
    assert _val(out, "S1", "exclusion_error", b) == pytest.approx(0.5)  # B parmi A, B
    assert _val(out, "S1", "inclusion_error", b) == pytest.approx(0.5)  # C parmi A, C
    assert _val(out, "S1", "recipients_count", b) == pytest.approx(20.0)


def test_targeting_person_basis_uses_person_weights(case):
    pop, sim = case
    pw = pd.DataFrame({"household_id": list("ABCD"), "person_weight": [30.0, 10.0, 20.0, 40.0]})
    out = t.scenario_targeting_and_cost(sim, pop, pw)
    b = m.BASIS_PERSON
    assert _val(out, "S1", "coverage_eligible", b) == pytest.approx(50 / 60)
    assert _val(out, "S1", "exclusion_error", b) == pytest.approx(10 / 40)
    assert _val(out, "S1", "inclusion_error", b) == pytest.approx(20 / 50)
    assert _val(out, "S1", "recipients_count", b) == pytest.approx(50.0)


def test_fiscal_cost_distinguishes_annual_monthly_and_sample(case):
    pop, sim = case
    out = t.scenario_targeting_and_cost(sim, pop)
    assert _val(out, "S1", "fiscal_cost_annual") == pytest.approx(12_000.0)  # 10 x (600 + 600)
    assert _val(out, "S1", "fiscal_cost_monthly_mean") == pytest.approx(1_000.0)
    assert _val(out, "S1", "fiscal_cost_annual_sample") == pytest.approx(1_200.0)


def test_cost_effectiveness_by_hand(case):
    pop, sim = case
    out = t.scenario_targeting_and_cost(sim, pop)
    line = 4667 / 12
    gap_s0 = 12 * 10 * ((line - 100) + (line - 200))
    gap_s1 = 12 * 10 * ((line - 150) + (line - 200))
    assert _val(out, "S1", "poverty_gap_reduction_mad") == pytest.approx(gap_s0 - gap_s1)  # 6 000
    assert _val(out, "S1", "poverty_gap_reduction_per_mad") == pytest.approx(0.5)


def test_zero_spending_gives_nan_not_infinity():
    pop = _pop()
    sim = _sim(pop, {})  # aucun transfert
    out = t.scenario_targeting_and_cost(sim, pop)
    assert np.isnan(_val(out, "S1", "poverty_gap_reduction_per_mad"))
    assert np.isnan(_val(out, "S1", "inclusion_error", m.BASIS_HOUSEHOLD))  # aucun bénéficiaire
    assert _val(out, "S1", "fiscal_cost_annual") == 0.0
    assert not np.isinf(out["value"]).any()


def test_budget_utilization_and_enforcement(case):
    pop, sim = case
    out = t.scenario_targeting_and_cost(sim, pop, annual_budget=12_000.0)
    assert _val(out, "S1", "budget_utilization") == pytest.approx(1.0)
    out = t.scenario_targeting_and_cost(sim, pop, annual_budget=1_200.0, budget_basis="sample")
    assert _val(out, "S1", "budget_utilization") == pytest.approx(1.0)
    with pytest.raises(ValueError, match="Budget dépassé"):
        t.scenario_targeting_and_cost(sim, pop, annual_budget=11_000.0)
    with pytest.raises(ValueError, match="Budget dépassé"):
        t.scenario_targeting_and_cost(sim, pop, annual_budget=11_990.0)  # excès de 10 MAD > marge d'arrondi (2,4)
    # un excès de 0,5 MAD reste dans la marge d'arrondi au centime (0,005 x 12 x 40 = 2,4 MAD)
    out = t.scenario_targeting_and_cost(sim, pop, annual_budget=11_999.5)
    assert _val(out, "S1", "budget_utilization") == pytest.approx(12_000 / 11_999.5)
    with pytest.raises(ValueError):
        t.scenario_targeting_and_cost(sim, pop, annual_budget=1.0, budget_basis="autre")


def test_missing_s0_and_unknown_household_raise(case):
    pop, _ = case
    sim_no_s0 = _sim(pop, {"A": 50.0}, extra_s0=False)
    with pytest.raises(ValueError, match="S0"):
        t.scenario_targeting_and_cost(sim_no_s0, pop)
    sim = _sim(pop, {"A": 50.0})
    with pytest.raises(ValueError):
        t.scenario_targeting_and_cost(sim, pop.iloc[:3])


@pytest.mark.skipif(not (POP_MOCK.exists() and SIM_MOCK.exists()), reason="mock absente")
def test_mock_budget_is_respected_and_results_are_finite():
    pop = pd.read_csv(POP_MOCK, dtype={"household_id": str})
    sim = pd.read_csv(SIM_MOCK, dtype={"household_id": str})
    # budget fictif de la mock : 4 000 MAD par mois, réparti sur l'échantillon (somme brute)
    out = t.scenario_targeting_and_cost(sim, pop, annual_budget=4_000.0 * 12, budget_basis="sample")
    assert set(out.scenario_id) == {"S1", "S2", "S3"}
    util = out[out.metric == "budget_utilization"]["value"]
    assert (util <= 1.0001).all()  # écart d'arrondi au centime toléré (S2 : 1,0000025)
    assert out["value"].notna().all() and np.isfinite(out["value"]).all()
