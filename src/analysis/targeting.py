"""Ciblage, coût budgétaire et coût-efficacité (partie B, B4 à B6).

Définitions (docs/pending_decisions.md, D5, D6, D16) :
- Ménage bénéficiaire : transfer_total > 0 (somme des 12 mois) dans la réplication.
- Ménage éligible : eligible_baseline = 1 (Pauvre ou Vulnérable, D6).
- Ménage pauvre (référence du ciblage, D16) : equiv_consumption de population.csv sous le seuil du
  milieu (D5), c'est-à-dire avant toute simulation. Redonne les 499 ménages Pauvre du HCP.
- Couverture = bénéficiaires éligibles / éligibles.
- Erreur d'exclusion = pauvres non bénéficiaires / pauvres.
- Erreur d'inclusion = bénéficiaires non pauvres / bénéficiaires.
  Chaque taux existe en base « ménage » (household_weight) et en base « personne » (coef_indiv).
- Coût budgétaire : somme(household_weight x transferts sur 12 mois), en MAD, cumulé sur l'année
  (annuel = cumulé car l'horizon est de 12 mois) ; version non pondérée (échantillon) en plus.
- Coût-efficacité : réduction annuelle de l'écart de pauvreté (en MAD) par MAD dépensé. Numérateur
  et dénominateur utilisent household_weight (écart du ménage = taille x écart par personne),
  pour rester dans le même univers de pondération.

Règles explicites : dénominateur nul ou négatif -> NaN, jamais une valeur infinie ; budget dépassé -> ValueError.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis import metrics as m

MONTHS = 12
BASIS_HOUSEHOLD_SIZE = "ménage (poids ménage x taille)"
TIME_BASIS_RECIPIENT = "bénéficiaire = transfert > 0 au moins un mois sur 12"
TIME_BASIS_CUMULATIVE = "12 mois cumulés"
TIME_BASIS_CE = "12 mois (écart mensuel moyen x 12)"
CENT_ROUNDING = 0.005  # les fichiers arrondissent chaque transfert au centime : erreur maximale par ligne (MAD)


def _ratio(numerator: float, denominator: float) -> float:
    """Quotient ; NaN si le dénominateur est nul ou négatif (B6)."""
    return float("nan") if not denominator > 0 else float(numerator / denominator)


def _row(run_id, scenario_id, metric, value, basis, time_basis, denominator, notes) -> dict:
    return {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "metric": metric,
        "value": float(value),
        "weighting_basis": basis,
        "time_basis": time_basis,
        "denominator": float(denominator),
        "notes": notes,
    }


def _household_data(sim: pd.DataFrame, pop: pd.DataFrame, person_weights: pd.DataFrame | None) -> tuple[pd.DataFrame, dict]:
    outcomes = m.household_level_outcomes(sim)
    weights = m._weights_by_basis(pop, person_weights)
    attrs = pop[
        ["household_id", "urban_rural", "household_size", "household_weight", "equiv_consumption", "eligible_baseline"]
    ].rename(columns={"equiv_consumption": "equiv_baseline"})
    for key, (w, _) in weights.items():
        attrs[f"w_{key}"] = w.to_numpy()
    data = outcomes.merge(attrs, on="household_id", how="left", validate="many_to_one")
    if data["urban_rural"].isna().any():
        raise ValueError("Des household_id de la simulation sont absents de population.csv.")
    data["line"] = m.poverty_line_for(data["urban_rural"]).to_numpy()
    data["poor_baseline"] = data["equiv_baseline"] < data["line"]
    data["recipient"] = data["transfer_total"] > 0
    data["eligible"] = data["eligible_baseline"] == 1
    return data, weights


def targeting_metrics(data: pd.DataFrame, run_id, scenario_id, weights: dict) -> list[dict]:
    """Couverture, erreurs d'inclusion et d'exclusion, nombre de bénéficiaires (B4)."""
    rows: list[dict] = []
    for key, (_, label) in weights.items():
        w = data[f"w_{key}"].to_numpy(dtype=float)
        rec, elig, poor = data["recipient"].to_numpy(), data["eligible"].to_numpy(), data["poor_baseline"].to_numpy()
        unit = "ménages" if key == "household" else "personnes"
        d_elig, d_poor, d_rec = w[elig].sum(), w[poor].sum(), w[rec].sum()
        rows += [
            _row(run_id, scenario_id, "coverage_eligible", _ratio(w[rec & elig].sum(), d_elig), label,
                 TIME_BASIS_RECIPIENT, d_elig, f"bénéficiaires éligibles / éligibles ; dénominateur : {unit} éligibles"),
            _row(run_id, scenario_id, "exclusion_error", _ratio(w[poor & ~rec].sum(), d_poor), label,
                 TIME_BASIS_RECIPIENT, d_poor, f"pauvres non bénéficiaires / pauvres (D16) ; dénominateur : {unit} pauvres"),
            _row(run_id, scenario_id, "inclusion_error", _ratio(w[rec & ~poor].sum(), d_rec), label,
                 TIME_BASIS_RECIPIENT, d_rec, f"bénéficiaires non pauvres / bénéficiaires (D16) ; dénominateur : {unit} bénéficiaires"),
            _row(run_id, scenario_id, "recipients_count", d_rec, label,
                 TIME_BASIS_RECIPIENT, w.sum(), f"{unit} représentés recevant un transfert ; dénominateur : {unit} représentés"),
        ]
    return rows


def fiscal_cost_metrics(data: pd.DataFrame, run_id, scenario_id) -> tuple[list[dict], float, float]:
    """Dépenses payées (B5) : cumulées sur 12 mois, moyenne mensuelle, et somme non pondérée.

    Retourne aussi le coût annuel pondéré et le coût annuel non pondéré, pour le contrôle du budget.
    """
    paid_weighted = float((data["household_weight"] * data["transfer_total"]).sum())
    paid_sample = float(data["transfer_total"].sum())
    n_hh = float(data["household_weight"].sum())
    rows = [
        _row(run_id, scenario_id, "fiscal_cost_annual", paid_weighted, m.BASIS_HOUSEHOLD, TIME_BASIS_CUMULATIVE, n_hh,
             "MAD payés sur 12 mois, pondérés par household_weight (annuel = cumulé) ; dénominateur : ménages représentés"),
        _row(run_id, scenario_id, "fiscal_cost_monthly_mean", paid_weighted / MONTHS, m.BASIS_HOUSEHOLD,
             "moyenne mensuelle sur 12 mois", n_hh,
             "MAD par mois en moyenne, pondérés par household_weight ; dénominateur : ménages représentés"),
        _row(run_id, scenario_id, "fiscal_cost_annual_sample", paid_sample, "non pondéré", TIME_BASIS_CUMULATIVE,
             float(len(data)), "MAD payés sur 12 mois, somme brute sur l'échantillon ; dénominateur : ménages de l'échantillon"),
    ]
    return rows, paid_weighted, paid_sample


def check_budget(
    paid: float, annual_budget: float, budget_basis: str, run_id, scenario_id, rounding_allowance: float = 0.0
) -> None:
    """Le budget commun ne doit jamais être dépassé (maître, section 5).

    `rounding_allowance` (MAD) est la marge maximale due à l'arrondi au centime de chaque transfert
    mensuel : un excès plus petit n'est pas un dépassement, un excès plus grand l'est.
    """
    if paid > annual_budget + rounding_allowance:
        raise ValueError(
            f"Budget dépassé ({run_id}, {scenario_id}) : {paid:,.2f} MAD payés pour un budget "
            f"de {annual_budget:,.2f} MAD (base {budget_basis}, marge d'arrondi {rounding_allowance:,.2f})."
        )


def _gap_total_annual(data: pd.DataFrame) -> float:
    """Écart de pauvreté annuel agrégé en MAD : 12 x somme(poids ménage x taille x max(0, seuil - bien-être))."""
    gap = np.clip(data["line"].to_numpy() - data["equiv_outcome"].to_numpy(), 0, None)
    return float(MONTHS * (data["household_weight"] * data["household_size"] * gap).sum())


def scenario_targeting_and_cost(
    sim: pd.DataFrame,
    pop: pd.DataFrame,
    person_weights: pd.DataFrame | None = None,
    annual_budget: float | None = None,
    budget_basis: str = "weighted",
) -> pd.DataFrame:
    """Ciblage, coût et coût-efficacité par run et scénario de transfert (S1 à S3), format long.

    `annual_budget` (MAD par an) est facultatif : fourni, il sert à contrôler et à rapporter l'utilisation du budget.
    `budget_basis` : « weighted » (coût pondéré, national) ou « sample » (somme brute de l'échantillon).
    """
    if budget_basis not in {"weighted", "sample"}:
        raise ValueError("budget_basis doit valoir 'weighted' ou 'sample'.")
    data, weights = _household_data(sim, pop, person_weights)

    rows: list[dict] = []
    for run_id, run in data.groupby("run_id", sort=True):
        s0 = run[run["scenario_id"] == "S0"]
        if s0.empty:
            raise ValueError(f"Run {run_id} : le scénario S0 est nécessaire au coût-efficacité.")
        gap_s0 = _gap_total_annual(s0)
        for scenario_id, g in run.groupby("scenario_id", sort=True):
            if scenario_id == "S0":
                continue
            rows += targeting_metrics(g, run_id, scenario_id, weights)
            cost_rows, paid_weighted, paid_sample = fiscal_cost_metrics(g, run_id, scenario_id)
            rows += cost_rows
            if annual_budget is not None:
                paid = paid_weighted if budget_basis == "weighted" else paid_sample
                # au plus une ligne de transfert par ménage et par mois, arrondie au centime
                n_cells = float(len(g)) if budget_basis == "sample" else float(g["household_weight"].sum())
                check_budget(paid, annual_budget, budget_basis, run_id, scenario_id, CENT_ROUNDING * MONTHS * n_cells)
                rows.append(
                    _row(run_id, scenario_id, "budget_utilization", _ratio(paid, annual_budget),
                         m.BASIS_HOUSEHOLD if budget_basis == "weighted" else "non pondéré", TIME_BASIS_CUMULATIVE,
                         annual_budget, f"dépenses / budget annuel (base {budget_basis}) ; dénominateur : budget annuel en MAD"),
                )
            reduction = gap_s0 - _gap_total_annual(g)
            rows += [
                _row(run_id, scenario_id, "poverty_gap_reduction_mad", reduction, BASIS_HOUSEHOLD_SIZE, TIME_BASIS_CE,
                     gap_s0, "réduction annuelle de l'écart de pauvreté agrégé (S0 moins S) en MAD ; dénominateur : écart agrégé de S0"),
                _row(run_id, scenario_id, "poverty_gap_reduction_per_mad", _ratio(reduction, paid_weighted),
                     BASIS_HOUSEHOLD_SIZE, TIME_BASIS_CE, paid_weighted,
                     "MAD d'écart de pauvreté réduits par MAD dépensé ; NaN si aucune dépense ; dénominateur : coût annuel pondéré"),
            ]
    return pd.DataFrame(rows, columns=m.LONG_COLUMNS)
