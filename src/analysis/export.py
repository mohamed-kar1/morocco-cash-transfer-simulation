"""Assemblage et export de la partie B (B8) : scenario_metrics.csv, group_impacts.csv,
metric_definitions.csv et analysis_metadata.json.

Usage :
    python -m src.analysis.export --mock
    python -m src.analysis.export --simulation data/processed/simulation_results.csv --budget 1000000000

Le mode --mock lit les fichiers fictifs de data/mock/ et écrit des fichiers suffixés `_mock` : ils ne
doivent jamais être cités comme résultats. Une valeur vide dans `value` signifie « non défini »
(dénominateur nul, par exemple aucun bénéficiaire ou aucune dépense).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.analysis import metrics as m
from src.analysis import subgroups as sg
from src.analysis import targeting as t
from src.analysis import validate as v
from src.population import build_population as bp

POP_CSV = Path("data/processed/population.csv")
PW_CSV = Path("data/processed/person_weights.csv")
SIM_CSV = Path("data/processed/simulation_results.csv")
POP_MOCK = Path("data/mock/population_mock.csv")
SIM_MOCK = Path("data/mock/simulation_results_mock.csv")
OUT_DIR = Path("data/processed")
OUT_DIR_MOCK = Path("data/mock")
SORT_SCENARIO = ["run_id", "scenario_id", "metric", "weighting_basis"]
SORT_GROUP = ["run_id", "scenario_id", "subgroup_dimension", "subgroup_value", "metric", "weighting_basis"]

# Registre des indicateurs : source unique des définitions et des unités.
METRIC_DEFINITIONS: list[dict] = [
    {"metric": "poverty_headcount", "appears_in": "scenario_metrics, group_impacts", "unit": "part (0 à 1)",
     "definition": "Part pondérée des ménages (ou des personnes) dont la consommation équivalente par personne et par mois est strictement sous le seuil HCP du milieu (D5)."},
    {"metric": "poverty_gap", "appears_in": "scenario_metrics, group_impacts", "unit": "part du seuil (0 à 1)",
     "definition": "Écart moyen au seuil, en part du seuil, tous ménages confondus (0 pour les non-pauvres)."},
    {"metric": "gini", "appears_in": "scenario_metrics, group_impacts", "unit": "indice (0 à 1)",
     "definition": "Coefficient de Gini pondéré de la consommation équivalente par personne."},
    {"metric": "mean_equiv_consumption", "appears_in": "scenario_metrics, group_impacts", "unit": "MAD 2014 par personne et par mois",
     "definition": "Consommation équivalente moyenne pondérée."},
    {"metric": "coverage_eligible", "appears_in": "scenario_metrics", "unit": "part (0 à 1)",
     "definition": "Bénéficiaires éligibles / éligibles (eligible_baseline = 1) ; bénéficiaire = transfert > 0 au moins un mois (D16)."},
    {"metric": "exclusion_error", "appears_in": "scenario_metrics", "unit": "part (0 à 1)",
     "definition": "Ménages (ou personnes) pauvres au départ non bénéficiaires / pauvres au départ (D16)."},
    {"metric": "inclusion_error", "appears_in": "scenario_metrics", "unit": "part (0 à 1)",
     "definition": "Bénéficiaires non pauvres au départ / bénéficiaires (D16). Vide s'il n'y a aucun bénéficiaire."},
    {"metric": "recipients_count", "appears_in": "scenario_metrics", "unit": "ménages ou personnes représentés",
     "definition": "Nombre pondéré de bénéficiaires (transfert > 0 au moins un mois)."},
    {"metric": "fiscal_cost_annual", "appears_in": "scenario_metrics", "unit": "MAD par an",
     "definition": "Transferts payés sur 12 mois, pondérés par household_weight (annuel = cumulé sur l'horizon)."},
    {"metric": "fiscal_cost_monthly_mean", "appears_in": "scenario_metrics", "unit": "MAD par mois",
     "definition": "Coût annuel pondéré divisé par 12."},
    {"metric": "fiscal_cost_annual_sample", "appears_in": "scenario_metrics", "unit": "MAD par an",
     "definition": "Transferts payés sur 12 mois, somme brute sur les ménages de l'échantillon (non pondérée)."},
    {"metric": "budget_utilization", "appears_in": "scenario_metrics", "unit": "part (0 à 1)",
     "definition": "Dépenses / budget annuel commun, dans la base indiquée dans notes (D9, D15). Présent seulement si un budget est fourni."},
    {"metric": "poverty_gap_reduction_mad", "appears_in": "scenario_metrics", "unit": "MAD par an",
     "definition": "Écart de pauvreté agrégé de S0 moins celui du scénario, x 12 mois, pondéré par household_weight x taille."},
    {"metric": "poverty_gap_reduction_per_mad", "appears_in": "scenario_metrics", "unit": "MAD d'écart réduits par MAD dépensé",
     "definition": "poverty_gap_reduction_mad / fiscal_cost_annual. Vide si la dépense est nulle (D16, B6)."},
    {"metric": "group_households_unweighted", "appears_in": "group_impacts", "unit": "ménages",
     "definition": "Effectif non pondéré du groupe dans l'échantillon (sert à signaler les petits groupes, D12)."},
    {"metric": "group_households_weighted", "appears_in": "group_impacts", "unit": "ménages représentés",
     "definition": "Somme de household_weight dans le groupe."},
    {"metric": "group_persons_weighted", "appears_in": "group_impacts", "unit": "personnes représentées",
     "definition": "Somme du poids personne (coef_indiv, D14) dans le groupe."},
    {"metric": "<indicateur>_change_vs_S0", "appears_in": "scenario_metrics, group_impacts", "unit": "unité de l'indicateur",
     "definition": "Écart absolu avec S0 dans la même réplication (scénario moins S0). Absent pour S0."},
]
_DEFINED = {d["metric"] for d in METRIC_DEFINITIONS}
CHANGE_SUFFIX = "_change_vs_S0"


def is_defined(metric: str) -> bool:
    base = metric[: -len(CHANGE_SUFFIX)] if metric.endswith(CHANGE_SUFFIX) else metric
    return base in _DEFINED


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"household_id": str, "run_id": str, "scenario_id": str})


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_outputs(
    sim: pd.DataFrame,
    pop: pd.DataFrame,
    person_weights: pd.DataFrame | None = None,
    annual_budget: float | None = None,
    budget_basis: str = "weighted",
    min_n: int = sg.SMALL_GROUP_MIN,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Valide les entrées, calcule et assemble scenario_metrics et group_impacts (non écrits)."""
    bp.validate_contract(pop)
    if person_weights is not None:
        bp.validate_person_weights(person_weights, pop)
    v.validate_simulation_results(sim, pop)

    scenario = pd.concat(
        [
            m.baseline_metrics(pop, person_weights),
            m.scenario_metrics(sim, pop, person_weights),
            t.scenario_targeting_and_cost(sim, pop, person_weights, annual_budget, budget_basis),
        ],
        ignore_index=True,
    )
    groups = sg.group_impacts(sim, pop, person_weights, min_n)

    undefined = sorted({x for x in set(scenario["metric"]) | set(groups["metric"]) if not is_defined(x)})
    if undefined:
        raise ValueError(f"Indicateur(s) sans définition dans METRIC_DEFINITIONS : {undefined}")
    scenario = scenario.sort_values(SORT_SCENARIO, kind="mergesort").reset_index(drop=True)
    groups = groups.sort_values(SORT_GROUP, kind="mergesort").reset_index(drop=True)
    return scenario[m.LONG_COLUMNS], groups[sg.GROUP_COLUMNS]


def write_outputs(
    scenario: pd.DataFrame, groups: pd.DataFrame, out_dir: Path, suffix: str = "", metadata: dict | None = None
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "scenario_metrics": out_dir / f"scenario_metrics{suffix}.csv",
        "group_impacts": out_dir / f"group_impacts{suffix}.csv",
        "metric_definitions": out_dir / f"metric_definitions{suffix}.csv",
        "analysis_metadata": out_dir / f"analysis_metadata{suffix}.json",
    }
    scenario.to_csv(paths["scenario_metrics"], index=False, encoding="utf-8")
    groups.to_csv(paths["group_impacts"], index=False, encoding="utf-8")
    pd.DataFrame(METRIC_DEFINITIONS).to_csv(paths["metric_definitions"], index=False, encoding="utf-8")
    meta = dict(metadata or {})
    meta["outputs"] = {"scenario_metrics_rows": len(scenario), "group_impacts_rows": len(groups)}
    paths["analysis_metadata"].write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return paths


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Calcule et exporte scenario_metrics.csv et group_impacts.csv.")
    ap.add_argument("--mock", action="store_true", help="utiliser les fichiers fictifs de data/mock/")
    ap.add_argument("--simulation", type=Path, default=None, help="chemin de simulation_results.csv")
    ap.add_argument("--population", type=Path, default=None)
    ap.add_argument("--person-weights", type=Path, default=None)
    ap.add_argument("--budget", type=float, default=None, help="budget annuel commun en MAD (contrôle et utilisation)")
    ap.add_argument("--budget-basis", choices=["weighted", "sample"], default="weighted")
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.mock:
        from src.analysis.mock_simulation import MONTHLY_BUDGET

        pop_path = args.population or POP_MOCK
        sim_path = args.simulation or SIM_MOCK
        pw_path = args.person_weights  # la mock n'a pas de coef_indiv : base personne approximée
        budget = args.budget if args.budget is not None else MONTHLY_BUDGET * 12
        basis = "sample" if args.budget is None else args.budget_basis
        out_dir, suffix = args.out_dir or OUT_DIR_MOCK, "_mock"
    else:
        pop_path = args.population or POP_CSV
        sim_path = args.simulation or SIM_CSV
        pw_path = args.person_weights or PW_CSV
        budget, basis = args.budget, args.budget_basis
        out_dir, suffix = args.out_dir or OUT_DIR, ""

    needed = [pop_path, sim_path] + ([pw_path] if pw_path else [])
    missing = [str(p) for p in needed if not Path(p).exists()]
    if missing:
        raise SystemExit("Fichier(s) introuvable(s) : " + ", ".join(missing))

    pop, sim = _read(pop_path), _read(sim_path)
    pw = _read(pw_path) if pw_path else None
    scenario, groups = build_outputs(sim, pop, pw, budget, basis)

    inputs = {"population": pop_path, "simulation_results": sim_path}
    if pw_path:
        inputs["person_weights"] = pw_path
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "mock (données fictives, ne pas citer)" if args.mock else "réel",
        "inputs": {k: {"path": str(p), "sha256": _sha256(Path(p))} for k, p in inputs.items()},
        "input_rows": {"population": len(pop), "simulation_results": len(sim)},
        "runs": sorted(sim["run_id"].unique().tolist()),
        "scenarios": sorted(sim["scenario_id"].unique().tolist()),
        "annual_budget": budget,
        "budget_basis": basis if budget is not None else None,
        "small_group_min_households": sg.SMALL_GROUP_MIN,
        "person_basis": "coef_indiv (person_weights.csv)" if pw_path else "approximation : household_weight x household_size",
    }
    paths = write_outputs(scenario, groups, out_dir, suffix, metadata)
    print(f"scenario_metrics : {len(scenario)} lignes -> {paths['scenario_metrics']}")
    print(f"group_impacts : {len(groups)} lignes -> {paths['group_impacts']}")
    print(f"Définitions : {paths['metric_definitions']} ; traçabilité : {paths['analysis_metadata']}")


if __name__ == "__main__":
    main()
