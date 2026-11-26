from pathlib import Path

import pandas as pd
import pytest

from src.analysis import mock_simulation as m

POP = Path("data/mock/population_mock.csv")


@pytest.fixture(scope="module")
def pop():
    return pd.read_csv(POP, dtype={"household_id": str})


@pytest.fixture(scope="module")
def sim(pop):
    return m.build_mock_simulation(pop)


def test_columns_and_grain(pop, sim):
    assert list(sim.columns) == m.COLUMNS
    assert len(sim) == len(pop) * m.MONTHS * len(m.SCENARIOS) * len(m.REPLICATIONS)
    assert not sim.duplicated(["run_id", "scenario_id", "month", "household_id"]).any()
    assert sim.isna().sum().sum() == 0


def test_s0_pays_nothing_and_only_eligible_are_paid(sim):
    assert (sim.loc[sim.scenario_id == "S0", "transfer_amount"] == 0).all()
    assert (sim.loc[sim.eligible_baseline == 0, "transfer_amount"] == 0).all()


def test_same_budget_for_s1_s2_s3(sim):
    spent = sim[sim.scenario_id != "S0"].groupby(["run_id", "scenario_id", "month"])["transfer_amount"].sum()
    assert spent.round(0).eq(m.MONTHLY_BUDGET).all()


def test_same_shocks_across_scenarios(sim):
    p = sim.pivot_table(index=["run_id", "month", "household_id"], columns="scenario_id", values="economic_shock")
    assert p.nunique(axis=1).eq(1).all()


def test_s2_follows_household_size_and_s3_follows_gap(pop):
    s2 = m.monthly_transfers(pop, "S2")
    elig = pop[pop.eligible_baseline == 1]
    a, b = elig.household_size.idxmax(), elig.household_size.idxmin()
    assert s2[a] > s2[b]
    s3 = m.monthly_transfers(pop, "S3")
    line = pop.urban_rural.map(m.POVERTY_LINE_MONTHLY)
    above = pop[(pop.eligible_baseline == 1) & (pop.equiv_consumption >= line)].index
    assert (s3[above] == 0).all()  # au-dessus du seuil : écart nul


def test_identities(sim):
    assert ((sim.disposable_resources - (sim.economic_shock + sim.transfer_amount)) > 0).all()
    assert (sim.consumption_outcome >= 0).all()
    ratio = sim.consumption_outcome / sim.equiv_consumption_outcome
    assert ratio.between(1, 12.1).all()  # facteur d'équivalence = taille du ménage
