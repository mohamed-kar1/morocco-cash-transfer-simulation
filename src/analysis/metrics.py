"""Indicateurs distributifs pondérés (partie B, B2 et B3).

Définitions (voir docs/pending_decisions.md, D5, D7, D13, D15, D16) :
- Bien-être : consommation équivalente par personne et par mois (MAD de 2014).
- Seuil de pauvreté mensuel par personne : 4 667 / 12 (urbain), 4 312 / 12 (rural) (D5).
  Un ménage est pauvre si son bien-être est strictement inférieur au seuil (règle du HCP).
- Taux de pauvreté (headcount) = somme(poids x 1[pauvre]) / somme(poids).
- Écart de pauvreté (poverty gap, FGT1) = somme(poids x max(0, seuil - bien-être) / seuil) / somme(poids).
- Gini : coefficient de Gini pondéré, courbe de Lorenz (trapèzes), bien-être >= 0.
- Base de pondération : « ménage » (household_weight) ou « personne » (coef_indiv, D7).
- Base de temps d'une simulation : moyenne des 12 mois du bien-être équivalent de chaque ménage.

Règles explicites : valeurs manquantes, poids négatifs ou longueurs différentes -> ValueError ;
dénominateur nul (somme des poids = 0) -> NaN, jamais une valeur infinie.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

POVERTY_LINE_MONTHLY = {"urbain": 4667 / 12, "rural": 4312 / 12}  # MAD par personne et par mois (D5)
MONTHS = 12
METRICS = ["poverty_headcount", "poverty_gap", "gini", "mean_equiv_consumption"]
LONG_COLUMNS = [
    "run_id", "scenario_id", "metric", "value", "weighting_basis", "time_basis", "denominator", "notes",
]

BASIS_HOUSEHOLD = "ménage"
BASIS_PERSON = "personne"
BASIS_PERSON_APPROX = "personne (approx.)"
TIME_BASIS_SCENARIO = "moyenne des 12 mois"
TIME_BASIS_BASELINE = "DAM / 12 (valeur annuelle ramenée au mois)"


# ----------------------------------------------------------------------------- primitives


def _prepare(x, w) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=float)
    w = np.asarray(w, dtype=float)
    if x.shape != w.shape:
        raise ValueError("Les valeurs et les poids doivent avoir la même longueur.")
    if np.isnan(x).any() or np.isnan(w).any():
        raise ValueError("Valeurs ou poids manquants : à traiter avant le calcul.")
    if (w < 0).any():
        raise ValueError("Poids négatifs interdits.")
    return x, w


def weighted_mean(x, w) -> float:
    x, w = _prepare(x, w)
    total = w.sum()
    return float("nan") if total == 0 else float((x * w).sum() / total)


def poverty_headcount(x, line, w) -> float:
    """Part pondérée de la population dont le bien-être est strictement sous le seuil."""
    x, w = _prepare(x, w)
    line = np.broadcast_to(np.asarray(line, dtype=float), x.shape)
    total = w.sum()
    return float("nan") if total == 0 else float((w * (x < line)).sum() / total)


def poverty_gap(x, line, w) -> float:
    """Écart de pauvreté normalisé (FGT1) : écart moyen au seuil, en part du seuil."""
    x, w = _prepare(x, w)
    line = np.broadcast_to(np.asarray(line, dtype=float), x.shape)
    if (line <= 0).any():
        raise ValueError("Le seuil de pauvreté doit être strictement positif.")
    total = w.sum()
    if total == 0:
        return float("nan")
    return float((w * np.clip(line - x, 0, None) / line).sum() / total)


def poverty_gap_total(x, line, w) -> float:
    """Écart de pauvreté agrégé en MAD par mois : somme(poids x max(0, seuil - bien-être)).

    Sert au rapport coût-efficacité (B6) ; ne pas confondre avec l'indice normalisé.
    """
    x, w = _prepare(x, w)
    line = np.broadcast_to(np.asarray(line, dtype=float), x.shape)
    return float((w * np.clip(line - x, 0, None)).sum())


def gini(x, w) -> float:
    """Gini pondéré par la courbe de Lorenz (trapèzes). NaN si le total pondéré est nul."""
    x, w = _prepare(x, w)
    if (x < 0).any():
        raise ValueError("Gini non défini pour des valeurs négatives.")
    keep = w > 0
    x, w = x[keep], w[keep]
    if w.size == 0 or (w * x).sum() == 0:
        return float("nan")
    order = np.argsort(x, kind="mergesort")
    x, w = x[order], w[order]
    p = np.concatenate([[0.0], np.cumsum(w) / w.sum()])
    lorenz = np.concatenate([[0.0], np.cumsum(w * x) / (w * x).sum()])
    return float(1.0 - np.sum(np.diff(p) * (lorenz[1:] + lorenz[:-1])))


def distribution_metrics(x, line, w) -> dict:
    """Les quatre indicateurs de base pour une distribution et un jeu de poids."""
    x, w = _prepare(x, w)
    return {
        "poverty_headcount": poverty_headcount(x, line, w),
        "poverty_gap": poverty_gap(x, line, w),
        "gini": gini(x, w),
        "mean_equiv_consumption": weighted_mean(x, w),
        "denominator": float(w.sum()),
    }


# ----------------------------------------------------------------------------- poids et seuils


def poverty_line_for(urban_rural: pd.Series) -> pd.Series:
    line = urban_rural.map(POVERTY_LINE_MONTHLY)
    if line.isna().any():
        raise ValueError("urban_rural : modalité inconnue (attendu urbain ou rural).")
    return line.astype(float)


def person_weights_for(pop: pd.DataFrame, person_weights: pd.DataFrame | None = None) -> tuple[pd.Series, str]:
    """Poids personne par ménage, dans l'ordre de `pop`, avec le libellé de la base.

    Avec `person_weights.csv` (coef_indiv, D14) : base « personne ». Sans lui (fixture fictive) :
    household_weight x household_size, signalé comme approximation.
    """
    if person_weights is None:
        w = pop["household_weight"].astype(float) * pop["household_size"].astype(float)
        return w, BASIS_PERSON_APPROX
    merged = pop[["household_id"]].merge(person_weights, on="household_id", how="left")
    if merged["person_weight"].isna().any():
        raise ValueError("person_weights : des household_id de la population n'ont pas de poids personne.")
    return pd.Series(merged["person_weight"].to_numpy(), index=pop.index), BASIS_PERSON


def _weights_by_basis(pop: pd.DataFrame, person_weights: pd.DataFrame | None) -> dict[str, tuple[pd.Series, str]]:
    pw, person_label = person_weights_for(pop, person_weights)
    return {
        "household": (pop["household_weight"].astype(float), BASIS_HOUSEHOLD),
        "person": (pw, person_label),
    }


def _rows(run_id, scenario_id, values: dict, basis_label: str, time_basis: str, notes: str = "") -> list[dict]:
    unit = "ménages représentés" if basis_label == BASIS_HOUSEHOLD else "personnes représentées"
    return [
        {
            "run_id": run_id,
            "scenario_id": scenario_id,
            "metric": name,
            "value": values[name],
            "weighting_basis": basis_label,
            "time_basis": time_basis,
            "denominator": values["denominator"],
            "notes": (notes + " " if notes else "") + f"dénominateur : {unit}",
        }
        for name in METRICS
    ]


# ----------------------------------------------------------------------------- niveaux


def baseline_metrics(pop: pd.DataFrame, person_weights: pd.DataFrame | None = None) -> pd.DataFrame:
    """Indicateurs de base calculés sur population.csv (B2), avant toute simulation."""
    line = poverty_line_for(pop["urban_rural"]).to_numpy()
    x = pop["equiv_consumption"].to_numpy(dtype=float)
    rows: list[dict] = []
    for _, (w, label) in _weights_by_basis(pop, person_weights).items():
        rows += _rows("population", "baseline", distribution_metrics(x, line, w.to_numpy()), label, TIME_BASIS_BASELINE)
    return pd.DataFrame(rows, columns=LONG_COLUMNS)


def household_level_outcomes(sim: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par run, scénario et ménage : bien-être moyen sur les mois et transferts cumulés (MAD)."""
    return (
        sim.groupby(["run_id", "scenario_id", "household_id"], sort=True)
        .agg(
            equiv_outcome=("equiv_consumption_outcome", "mean"),
            transfer_total=("transfer_amount", "sum"),
            months=("month", "nunique"),
        )
        .reset_index()
    )


def scenario_metrics(
    sim: pd.DataFrame, pop: pd.DataFrame, person_weights: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Indicateurs par run et scénario, en format long (B3), avec les écarts par rapport à S0."""
    outcomes = household_level_outcomes(sim)
    weights = _weights_by_basis(pop, person_weights)
    attrs = pop[["household_id", "urban_rural"]].copy()
    for key, (w, _) in weights.items():
        attrs[f"w_{key}"] = w.to_numpy()
    data = outcomes.merge(attrs, on="household_id", how="left", validate="many_to_one")
    if data["urban_rural"].isna().any():
        raise ValueError("Des household_id de la simulation sont absents de population.csv.")
    data["line"] = poverty_line_for(data["urban_rural"]).to_numpy()

    rows: list[dict] = []
    for (run_id, scenario_id), g in data.groupby(["run_id", "scenario_id"], sort=True):
        for key, (_, label) in weights.items():
            vals = distribution_metrics(g["equiv_outcome"].to_numpy(), g["line"].to_numpy(), g[f"w_{key}"].to_numpy())
            rows += _rows(run_id, scenario_id, vals, label, TIME_BASIS_SCENARIO)
    levels = pd.DataFrame(rows, columns=LONG_COLUMNS)
    return pd.concat([levels, changes_vs_s0(levels)], ignore_index=True)


def changes_vs_s0(levels: pd.DataFrame) -> pd.DataFrame:
    """Écart absolu entre chaque scénario et S0 (même run, même indicateur, même base)."""
    keys = ["run_id", "metric", "weighting_basis", "time_basis"]
    s0 = levels[levels["scenario_id"] == "S0"].set_index(keys)["value"]
    other = levels[levels["scenario_id"] != "S0"].copy()
    if other.empty:
        return pd.DataFrame(columns=LONG_COLUMNS)
    base = s0.reindex(pd.MultiIndex.from_frame(other[keys])).to_numpy()
    other["value"] = other["value"].to_numpy() - base
    other["metric"] = other["metric"] + "_change_vs_S0"
    other["notes"] = "écart absolu avec S0 (scénario moins S0) ; " + other["notes"]
    return other[LONG_COLUMNS]
