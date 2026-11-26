"""Résultats par sous-groupe (partie B, B7) : format de group_impacts.csv.

Dimensions : urban_rural, region, household_size_group (1 à 6, puis 7+), has_children
(children_count > 0) et eligible_baseline. Pour chaque groupe, on calcule les quatre indicateurs de
metrics.py (en base ménage et en base personne), leur écart par rapport à S0, et on rapporte les
effectifs pondérés et non pondérés.

Règle des petits groupes (D12) : un groupe de moins de 500 ménages non pondérés est signalé dans la
colonne `notes` de chacune de ses lignes (« effectif faible ») ; il n'est jamais supprimé.
Les effectifs de groupes (lignes `group_households_*`) sont donnés une fois, pour run_id = population.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis import metrics as m

SMALL_GROUP_MIN = 500  # ménages non pondérés (D12)
DIMENSIONS = ["urban_rural", "region", "household_size_group", "has_children", "eligible_baseline"]
GROUP_COLUMNS = [
    "run_id", "scenario_id", "subgroup_dimension", "subgroup_value", "metric", "value",
    "weighting_basis", "denominator", "notes",
]
BASIS_UNWEIGHTED = "non pondéré"


def size_group(size: pd.Series) -> pd.Series:
    """Taille du ménage regroupée : 1, 2, 3, 4, 5, 6 et 7+."""
    return size.astype(int).map(lambda s: "7+" if s >= 7 else str(s))


def add_group_columns(pop: pd.DataFrame) -> pd.DataFrame:
    """Une colonne par dimension de sous-groupe, dans l'ordre de `pop`."""
    g = pd.DataFrame({"household_id": pop["household_id"].to_numpy()}, index=pop.index)
    g["urban_rural"] = pop["urban_rural"]
    g["region"] = pop["region"]
    g["household_size_group"] = size_group(pop["household_size"])
    g["has_children"] = np.where(pop["children_count"] > 0, "avec enfants", "sans enfant")
    g["eligible_baseline"] = np.where(pop["eligible_baseline"] == 1, "éligible", "non éligible")
    return g


def _note(unit: str, n_unweighted: int, min_n: int, extra: str = "") -> str:
    text = (extra + " ; " if extra else "") + f"dénominateur : {unit}"
    if n_unweighted < min_n:
        text += f" ; effectif faible : {n_unweighted} ménages non pondérés (< {min_n}), résultat instable (D12)"
    return text


def group_sizes(pop: pd.DataFrame, person_weights: pd.DataFrame | None = None, min_n: int = SMALL_GROUP_MIN) -> pd.DataFrame:
    """Effectifs de chaque groupe : non pondéré, pondéré (ménages) et pondéré (personnes)."""
    groups = add_group_columns(pop)
    weights = m._weights_by_basis(pop, person_weights)
    w_hh = weights["household"][0].to_numpy()
    w_pe, person_label = weights["person"][0].to_numpy(), weights["person"][1]
    n_total, hh_total, pe_total = len(pop), float(w_hh.sum()), float(w_pe.sum())
    rows: list[dict] = []
    for dim in DIMENSIONS:
        for value, idx in groups.groupby(dim).indices.items():
            n = len(idx)
            for metric, val, basis, denom, unit in [
                ("group_households_unweighted", float(n), BASIS_UNWEIGHTED, n_total, "ménages de l'échantillon"),
                ("group_households_weighted", float(w_hh[idx].sum()), m.BASIS_HOUSEHOLD, hh_total, "ménages représentés"),
                ("group_persons_weighted", float(w_pe[idx].sum()), person_label, pe_total, "personnes représentées"),
            ]:
                rows.append(
                    {"run_id": "population", "scenario_id": "baseline", "subgroup_dimension": dim,
                     "subgroup_value": value, "metric": metric, "value": val, "weighting_basis": basis,
                     "denominator": float(denom), "notes": _note(unit, n, min_n, "effectif du groupe")}
                )
    return pd.DataFrame(rows, columns=GROUP_COLUMNS)


def _metric_rows(run_id, scenario_id, frame: pd.DataFrame, x_col: str, weights: dict, counts: dict, min_n: int, time_note: str) -> list[dict]:
    rows: list[dict] = []
    x_all = frame[x_col].to_numpy(dtype=float)
    line_all = frame["line"].to_numpy(dtype=float)
    for dim in DIMENSIONS:
        for value, idx in frame.groupby(dim).indices.items():
            n = counts[(dim, value)]
            for key, (_, label) in weights.items():
                vals = m.distribution_metrics(x_all[idx], line_all[idx], frame[f"w_{key}"].to_numpy(dtype=float)[idx])
                unit = "ménages représentés" if key == "household" else "personnes représentées"
                for name in m.METRICS:
                    rows.append(
                        {"run_id": run_id, "scenario_id": scenario_id, "subgroup_dimension": dim,
                         "subgroup_value": value, "metric": name, "value": vals[name], "weighting_basis": label,
                         "denominator": vals["denominator"], "notes": _note(unit, n, min_n, time_note)}
                    )
    return rows


def _group_changes_vs_s0(levels: pd.DataFrame) -> pd.DataFrame:
    keys = ["run_id", "subgroup_dimension", "subgroup_value", "metric", "weighting_basis"]
    s0 = levels[levels["scenario_id"] == "S0"].set_index(keys)["value"]
    other = levels[levels["scenario_id"] != "S0"].copy()
    if other.empty:
        return pd.DataFrame(columns=GROUP_COLUMNS)
    base = s0.reindex(pd.MultiIndex.from_frame(other[keys])).to_numpy()
    other["value"] = other["value"].to_numpy() - base
    other["metric"] = other["metric"] + "_change_vs_S0"
    other["notes"] = "écart absolu avec S0 (scénario moins S0) ; " + other["notes"]
    return other[GROUP_COLUMNS]


def _prepare(pop: pd.DataFrame, person_weights: pd.DataFrame | None):
    groups = add_group_columns(pop)
    weights = m._weights_by_basis(pop, person_weights)
    counts = {
        (dim, value): len(idx)
        for dim in DIMENSIONS
        for value, idx in groups.groupby(dim).indices.items()
    }
    attrs = groups.copy()
    attrs["equiv_baseline"] = pop["equiv_consumption"].to_numpy(dtype=float)
    attrs["line"] = m.poverty_line_for(pop["urban_rural"]).to_numpy()
    for key, (w, _) in weights.items():
        attrs[f"w_{key}"] = w.to_numpy()
    return weights, counts, attrs


def baseline_group_impacts(
    pop: pd.DataFrame, person_weights: pd.DataFrame | None = None, min_n: int = SMALL_GROUP_MIN
) -> pd.DataFrame:
    """Effectifs et indicateurs de base par groupe, calculés sur population.csv (avant simulation)."""
    weights, counts, attrs = _prepare(pop, person_weights)
    baseline = _metric_rows(
        "population", "baseline", attrs.reset_index(drop=True), "equiv_baseline", weights, counts, min_n,
        m.TIME_BASIS_BASELINE,
    )
    return pd.concat(
        [group_sizes(pop, person_weights, min_n), pd.DataFrame(baseline, columns=GROUP_COLUMNS)], ignore_index=True
    )


def group_impacts(
    sim: pd.DataFrame,
    pop: pd.DataFrame,
    person_weights: pd.DataFrame | None = None,
    min_n: int = SMALL_GROUP_MIN,
) -> pd.DataFrame:
    """Indicateurs par groupe : situation de base, niveaux par scénario, écarts avec S0 et effectifs."""
    weights, counts, attrs = _prepare(pop, person_weights)

    outcomes = m.household_level_outcomes(sim)
    data = outcomes.merge(attrs, on="household_id", how="left", validate="many_to_one")
    if data["urban_rural"].isna().any():
        raise ValueError("Des household_id de la simulation sont absents de population.csv.")
    level_rows: list[dict] = []
    for (run_id, scenario_id), g in data.groupby(["run_id", "scenario_id"], sort=True):
        level_rows += _metric_rows(
            run_id, scenario_id, g.reset_index(drop=True), "equiv_outcome", weights, counts, min_n, m.TIME_BASIS_SCENARIO
        )
    levels = pd.DataFrame(level_rows, columns=GROUP_COLUMNS)
    return pd.concat(
        [baseline_group_impacts(pop, person_weights, min_n), levels, _group_changes_vs_s0(levels)],
        ignore_index=True,
    )
