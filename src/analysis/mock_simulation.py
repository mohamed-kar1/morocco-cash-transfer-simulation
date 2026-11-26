"""Génère un simulation_results.csv FICTIF à partir de la population mock.

Sert uniquement à tester les métriques de la partie B (src/analysis/) tant que le
simulateur de Personne 2 n'est pas prêt. Les règles ci-dessous (budget, formules S1 à S3,
chocs, réponse de consommation) sont des hypothèses d'illustration, pas des résultats :
les vraies règles sont celles de Personne 2 (D9 à D11).

Grain : une ligne = ménage x mois x scénario x réplication.

Usage : python -m src.analysis.mock_simulation
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POP_MOCK = Path("data/mock/population_mock.csv")
OUT_MOCK = Path("data/mock/simulation_results_mock.csv")

COLUMNS = [
    "run_id", "scenario_id", "seed", "month", "household_id", "household_weight",
    "economic_shock", "transfer_amount", "disposable_resources", "consumption_outcome",
    "equiv_consumption_outcome", "eligible_baseline",
]
SCENARIOS = ["S0", "S1", "S2", "S3"]
REPLICATIONS = {"R1": 42, "R2": 43}  # run_id -> graine
MONTHS = 12
MONTHLY_BUDGET = 4000.0  # MAD par mois, fictif (D9)
PROPENSITY_TO_CONSUME = 0.8  # fictif (D11)
SHOCK_PROBABILITY = 0.2
POVERTY_LINE_MONTHLY = {"urbain": 4667 / 12, "rural": 4312 / 12}  # D5, par personne et par mois


def monthly_transfers(pop: pd.DataFrame, scenario: str, budget: float = MONTHLY_BUDGET) -> pd.Series:
    """Transfert mensuel par ménage ; le budget est le même pour S1, S2 et S3."""
    elig = (pop["eligible_baseline"] == 1).astype(float)
    if scenario == "S0":
        return pd.Series(0.0, index=pop.index)
    if scenario == "S1":
        weight = elig
    elif scenario == "S2":
        weight = pop["household_size"] * elig
    elif scenario == "S3":
        line = pop["urban_rural"].map(POVERTY_LINE_MONTHLY)
        weight = (line - pop["equiv_consumption"]).clip(lower=0) * pop["household_size"] * elig
        if weight.sum() == 0:  # personne sous le seuil : repli sur un transfert égal
            weight = elig
    else:
        raise ValueError(f"Scénario inconnu : {scenario}")
    return budget * weight / weight.sum()


def draw_shocks(pop: pd.DataFrame, seed: int) -> np.ndarray:
    """Chocs (MAD, <= 0), tableau mois x ménage ; identiques dans les 4 scénarios d'une réplication."""
    rng = np.random.default_rng(seed)
    hit = rng.random((MONTHS, len(pop))) < SHOCK_PROBABILITY
    share = rng.uniform(0.05, 0.30, (MONTHS, len(pop)))
    return -(hit * share * pop["baseline_consumption"].to_numpy())


def build_mock_simulation(pop: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for run_id, seed in REPLICATIONS.items():
        shocks = draw_shocks(pop, seed)
        for scenario in SCENARIOS:
            transfer = monthly_transfers(pop, scenario).to_numpy()
            for m in range(MONTHS):
                shock = shocks[m]
                baseline = pop["baseline_consumption"].to_numpy()
                consumption = np.clip(baseline + shock, 0, None) + PROPENSITY_TO_CONSUME * transfer
                frames.append(pd.DataFrame({
                    "run_id": run_id,
                    "scenario_id": scenario,
                    "seed": seed,
                    "month": m + 1,
                    "household_id": pop["household_id"].to_numpy(),
                    "household_weight": pop["household_weight"].to_numpy(),
                    "economic_shock": shock.round(2) + 0.0,  # + 0.0 évite le « -0.0 »
                    "transfer_amount": transfer.round(2),
                    "disposable_resources": (baseline + shock + transfer).round(2),
                    "consumption_outcome": consumption.round(2),
                    "equiv_consumption_outcome": (consumption / pop["equivalence_factor"].to_numpy()).round(2),
                    "eligible_baseline": pop["eligible_baseline"].to_numpy(),
                }))
    return pd.concat(frames, ignore_index=True)[COLUMNS]


def main() -> None:
    pop = pd.read_csv(POP_MOCK, dtype={"household_id": str})
    sim = build_mock_simulation(pop)
    OUT_MOCK.parent.mkdir(parents=True, exist_ok=True)
    sim.to_csv(OUT_MOCK, index=False, encoding="utf-8")
    print(f"{len(sim)} lignes -> {OUT_MOCK}")


if __name__ == "__main__":
    main()
