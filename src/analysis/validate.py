"""Validation des entrées de la partie B (B1) : simulation_results.csv face à population.csv.

Convention exigée par l'analyse (D15) : une ligne par ménage, mois, scénario et réplication ;
montants en MAD par mois ; equiv_consumption_outcome = consumption_outcome / equivalence_factor.
Toute entorse arrête l'analyse avec un message clair : rien n'est corrigé en silence.
"""
from __future__ import annotations

import pandas as pd

SIM_COLUMNS = [
    "run_id", "scenario_id", "seed", "month", "household_id", "household_weight",
    "economic_shock", "transfer_amount", "disposable_resources", "consumption_outcome",
    "equiv_consumption_outcome", "eligible_baseline",
]
SCENARIOS = {"S0", "S1", "S2", "S3"}
KEY = ["run_id", "scenario_id", "month", "household_id"]
MONTHS = 12
EQUIV_TOLERANCE = 0.011  # arrondi à 2 décimales dans le fichier


def validate_simulation_results(sim: pd.DataFrame, pop: pd.DataFrame) -> None:
    problems: list[str] = []

    if list(sim.columns) != SIM_COLUMNS:
        raise ValueError(f"simulation_results : colonnes inattendues {list(sim.columns)}")
    if sim.isna().any().any():
        problems.append(f"{int(sim.isna().sum().sum())} valeur(s) manquante(s)")
    if sim.duplicated(KEY).any():
        problems.append(f"{int(sim.duplicated(KEY).sum())} doublon(s) sur {KEY}")
    unknown = set(sim["scenario_id"]) - SCENARIOS
    if unknown:
        problems.append(f"scénario(s) inconnu(s) : {sorted(unknown)}")
    if not sim["month"].between(1, MONTHS).all():
        problems.append(f"mois hors de 1 à {MONTHS}")
    if (sim["household_weight"] <= 0).any():
        problems.append("household_weight non positif")

    months_per_hh = sim.groupby(["run_id", "scenario_id", "household_id"])["month"].nunique()
    if (months_per_hh != MONTHS).any():
        problems.append(f"{int((months_per_hh != MONTHS).sum())} ménage(s) sans les {MONTHS} mois")

    missing_hh = set(sim["household_id"]) - set(pop["household_id"])
    if missing_hh:
        problems.append(f"{len(missing_hh)} household_id absent(s) de population.csv")

    if not problems:
        ref = pop.set_index("household_id")
        w_ref = sim["household_id"].map(ref["household_weight"])
        if ((sim["household_weight"] - w_ref).abs() > 1e-6).any():
            problems.append("household_weight différent de population.csv")
        if (sim["eligible_baseline"] != sim["household_id"].map(ref["eligible_baseline"])).any():
            problems.append("eligible_baseline différent de population.csv")
        expected = sim["consumption_outcome"] / sim["household_id"].map(ref["equivalence_factor"])
        if ((sim["equiv_consumption_outcome"] - expected).abs() > EQUIV_TOLERANCE).any():
            problems.append(
                "equiv_consumption_outcome != consumption_outcome / equivalence_factor (unités ou définition différentes ?)"
            )
        s0 = sim[sim["scenario_id"] == "S0"]
        if (s0["transfer_amount"] != 0).any():
            problems.append("S0 doit avoir des transferts nuls")
        if (sim["transfer_amount"] < 0).any():
            problems.append("transfer_amount négatif")

    if problems:
        raise ValueError("simulation_results invalide :\n- " + "\n- ".join(problems))
