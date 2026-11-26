"""Inspection reproductible de l'ENCDM 2014 (HCP).

Lit les fichiers SAV Ménage et Individus, exécute des contrôles d'intégrité et de
cohérence avec la note technique du HCP, puis écrit un rapport Markdown et JSON
dans outputs/inspection/. Le script ne modifie jamais les données brutes et
n'exporte que des agrégats (aucune ligne de microdonnées).

Usage :
    python -m src.population.inspect_data
    python -m src.population.inspect_data --help

Code de sortie : 0 si aucun contrôle bloquant n'échoue, 1 sinon, 2 si un fichier manque.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

# --- Noms de colonnes constatés dans les fichiers (voir docs/data_sources.md) -------------
HH_ID = "N_ménage"
W_HH = "coef_ménage"
W_IND = "coef_indiv"
MILIEU = "Milieu"
REGION = "Région_12"
SIZE = "Taille_ménage"
DAM = "DAM"
DAP = "DAP"
POOR = "Pauvre"
VULN = "Vulnérable"
AGE = "Age"

REQUIRED_HH = [HH_ID, W_HH, W_IND, MILIEU, REGION, SIZE, DAM, DAP, POOR, VULN]
REQUIRED_IND = [HH_ID, AGE]

# --- Chiffres de contrôle publiés dans la note technique du HCP ---------------------------
NOTE_N_HOUSEHOLDS = 15970
NOTE_SUM_W_HH = 7_190_456  # fréquence pondérée par coef_ménage
NOTE_MEAN_DAM_W_HH = 76317.23  # DAM moyenne, pondérée par coef_ménage
NOTE_MEAN_DAP_W_IND = 15875.68  # DAP moyenne, pondérée par coef_indiv

DEFAULT_DIR = Path("data/raw/encdm_2014")
DEFAULT_HH_FILE = "Ménage_ENCDM_2014_en_format_SAV.sav"
DEFAULT_IND_FILE = "Individus__ENCDM_2014_en_format_SAV.sav"
DEFAULT_OUT = Path("outputs/inspection")


# =========================================================================================
# Utilitaires
# =========================================================================================
def read_sav(path: Path) -> tuple[pd.DataFrame, object]:
    """Lit un fichier SAV avec les codes numériques bruts (sans appliquer les libellés)."""
    df, meta = pyreadstat.read_sav(str(path), apply_value_formats=False)
    return df, meta


def value_labels(meta: object, col: str) -> dict[float, str]:
    """Libellés des modalités d'une variable, avec clés numériques normalisées."""
    raw = getattr(meta, "variable_value_labels", {}).get(col, {})
    return {float(k): str(v) for k, v in raw.items()}


def weighted_mean(x: pd.Series, w: pd.Series) -> float:
    return float((x * w).sum() / w.sum())


def weighted_share(flag: pd.Series, w: pd.Series) -> float:
    """Part pondérée (en %) des observations où flag vaut 1."""
    return 100.0 * float((flag * w).sum() / w.sum())


def to_size(series: pd.Series) -> pd.Series:
    """Convertit une variable texte (avec espaces) en nombre ; NaN si impossible."""
    return pd.to_numeric(series.astype(str).str.strip(), errors="coerce")


def implied_poverty_cut(dap: pd.Series, poor: pd.Series) -> dict[str, float]:
    """Plus grande DAP des pauvres et plus petite DAP des non-pauvres (observation)."""
    return {
        "poor_max_dap": float(dap[poor == 1].max()),
        "nonpoor_min_dap": float(dap[poor == 0].min()),
    }


# =========================================================================================
# Contrôles
# =========================================================================================
def check_households(hh: pd.DataFrame, meta: object, min_cell: int) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    missing = [c for c in REQUIRED_HH if c not in hh.columns]
    if missing:
        return {"errors": [f"Colonnes manquantes dans le fichier Ménage : {missing}"], "warnings": []}

    res: dict = {"n_households": int(len(hh)), "n_columns": int(hh.shape[1])}

    # Identifiants
    res["id_unique"] = bool(hh[HH_ID].is_unique)
    if not res["id_unique"]:
        errors.append(f"{HH_ID} n'est pas unique.")
    if hh[HH_ID].isna().any():
        errors.append(f"{HH_ID} contient des valeurs manquantes.")

    # Poids
    for w in (W_HH, W_IND):
        if hh[w].isna().any() or not (hh[w] > 0).all():
            errors.append(f"{w} contient des valeurs manquantes ou non positives.")
    size = to_size(hh[SIZE])
    n_bad_size = int(size.isna().sum() + (size <= 0).sum())
    if n_bad_size:
        errors.append(f"{SIZE} : {n_bad_size} valeurs non convertibles ou non positives.")
    res["size"] = {"n_bad": n_bad_size, "min": float(size.min()), "max": float(size.max())}

    ratio = hh[W_IND] / (hh[W_HH] * size)
    res["weights"] = {
        "sum_w_hh": float(hh[W_HH].sum()),
        "sum_w_ind": float(hh[W_IND].sum()),
        "sum_w_hh_times_size": float((hh[W_HH] * size).sum()),
        "ratio_ind_over_hh_size_min": float(ratio.min()),
        "ratio_ind_over_hh_size_mean": float(ratio.mean()),
        "ratio_ind_over_hh_size_max": float(ratio.max()),
    }

    # Consommation
    if hh[DAM].isna().any() or not (hh[DAM] > 0).all():
        errors.append(f"{DAM} contient des valeurs manquantes ou non positives.")
    res["dam"] = {
        "min": float(hh[DAM].min()),
        "median": float(hh[DAM].median()),
        "max": float(hh[DAM].max()),
    }
    dap_gap = float((hh[DAP] - hh[DAM] / size).abs().max())
    res["dap_equals_dam_over_size_max_gap"] = dap_gap
    if dap_gap > 1e-6:
        warnings.append(f"{DAP} diffère de {DAM}/{SIZE} (écart max {dap_gap:.4f}).")

    # Réconciliation avec la note technique
    mean_dam_hh = weighted_mean(hh[DAM], hh[W_HH])
    mean_dap_ind = weighted_mean(hh[DAP], hh[W_IND])
    res["note_check"] = {
        "n_households": {"note": NOTE_N_HOUSEHOLDS, "data": int(len(hh))},
        "sum_w_hh": {"note": NOTE_SUM_W_HH, "data": float(hh[W_HH].sum())},
        "mean_dam_w_hh": {"note": NOTE_MEAN_DAM_W_HH, "data": mean_dam_hh},
        "mean_dap_w_ind": {"note": NOTE_MEAN_DAP_W_IND, "data": mean_dap_ind},
        "mean_dam_w_ind_alt": {"note": None, "data": weighted_mean(hh[DAM], hh[W_IND])},
        "mean_dap_w_hh_alt": {"note": None, "data": weighted_mean(hh[DAP], hh[W_HH])},
    }
    tol = {"n_households": 0, "sum_w_hh": 1, "mean_dam_w_hh": 0.01, "mean_dap_w_ind": 0.01}
    for key, t in tol.items():
        item = res["note_check"][key]
        item["ok"] = bool(abs(item["data"] - item["note"]) <= t)
        if not item["ok"]:
            warnings.append(f"Contrôle note technique non reproduit : {key} (note {item['note']}, données {item['data']:.2f}).")

    # Pauvreté (indicateurs HCP non documentés dans la note)
    for flag in (POOR, VULN):
        if not set(hh[flag].dropna().unique()) <= {0, 1}:
            errors.append(f"{flag} contient des valeurs autres que 0 et 1.")
    res["poverty"] = {
        "n_poor": int(hh[POOR].sum()),
        "n_vulnerable": int(hh[VULN].sum()),
        "n_poor_and_vulnerable": int(((hh[POOR] == 1) & (hh[VULN] == 1)).sum()),
        "poor_pct_w_hh": weighted_share(hh[POOR], hh[W_HH]),
        "poor_pct_w_ind": weighted_share(hh[POOR], hh[W_IND]),
        "vulnerable_pct_w_ind": weighted_share(hh[VULN], hh[W_IND]),
    }
    milieu_labels = value_labels(meta, MILIEU)
    cuts = {}
    for code in sorted(hh[MILIEU].dropna().unique()):
        sub = hh[hh[MILIEU] == code]
        label = milieu_labels.get(float(code), str(code))
        cuts[label] = implied_poverty_cut(sub[DAP], sub[POOR])
    res["implied_cut_by_milieu"] = cuts

    # Milieu et régions
    def group_table(col: str, labels: dict[float, str]) -> list[dict]:
        rows = []
        for code, sub in hh.groupby(col):
            rows.append(
                {
                    "code": float(code),
                    "label": labels.get(float(code), str(code)),
                    "n_households": int(len(sub)),
                    "sum_w_hh": float(sub[W_HH].sum()),
                    "poor_pct_w_ind": weighted_share(sub[POOR], sub[W_IND]),
                    "small_cell": bool(len(sub) < min_cell),
                }
            )
        return rows

    res["milieu"] = group_table(MILIEU, milieu_labels)
    res["region"] = group_table(REGION, value_labels(meta, REGION))
    small = [r["label"] for r in res["region"] if r["small_cell"]]
    if small:
        warnings.append(f"Régions sous {min_cell} ménages (non pondérés) : {', '.join(small)}.")
    res["min_cell"] = min_cell

    res["errors"], res["warnings"] = errors, warnings
    return res


def check_individuals(ind: pd.DataFrame, hh: pd.DataFrame) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    missing = [c for c in REQUIRED_IND if c not in ind.columns]
    if missing:
        return {"errors": [f"Colonnes manquantes dans le fichier Individus : {missing}"], "warnings": []}

    res: dict = {"n_persons": int(len(ind))}
    hh_ids, ind_ids = set(hh[HH_ID]), set(ind[HH_ID])
    only_hh, only_ind = hh_ids - ind_ids, ind_ids - hh_ids
    res["households_without_individuals"] = len(only_hh)
    res["individuals_without_household"] = len(only_ind)
    if only_hh or only_ind:
        errors.append(
            f"Identifiants non appariés : {len(only_hh)} ménages sans individus, "
            f"{len(only_ind)} identifiants individus sans ménage."
        )

    counts = ind.groupby(HH_ID).size()
    size = to_size(hh.set_index(HH_ID)[SIZE])
    matched = (counts.reindex(size.index) == size).fillna(False)
    res["size_matches_pct"] = 100.0 * float(matched.mean())
    if not matched.all():
        errors.append(f"{int((~matched).sum())} ménages dont la taille diffère du nombre de lignes Individus.")

    age = pd.to_numeric(ind[AGE], errors="coerce")
    res["age"] = {
        "n_missing": int(age.isna().sum()),
        "min": float(age.min()),
        "max": float(age.max()),
        "n_under_15": int((age < 15).sum()),
        "n_under_18": int((age < 18).sum()),
    }
    if res["age"]["n_missing"]:
        warnings.append(f"{res['age']['n_missing']} âges manquants dans Individus.")
    res["errors"], res["warnings"] = errors, warnings
    return res


# =========================================================================================
# Rapport
# =========================================================================================
def fint(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def fnum(x: float, nd: int = 2) -> str:
    return f"{x:,.{nd}f}".replace(",", " ")


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def build_markdown(hh_res: dict, ind_res: dict, files: dict) -> str:
    errors = hh_res.get("errors", []) + ind_res.get("errors", [])
    warnings = hh_res.get("warnings", []) + ind_res.get("warnings", [])
    status = "ÉCHEC" if errors else "OK"
    L = ["# Rapport d'inspection : ENCDM 2014", "", f"Statut : **{status}**", ""]
    L += ["Fichiers lus :", f"- Ménage : `{files['household']}`", f"- Individus : `{files['individual']}`", ""]

    if errors:
        L += ["## Erreurs bloquantes", *[f"- {e}" for e in errors], ""]
    if "n_households" not in hh_res:
        return "\n".join(L)

    L += ["## Intégrité", ""]
    L += [
        md_table(
            ["Contrôle", "Résultat"],
            [
                ["Ménages", fint(hh_res["n_households"])],
                ["Personnes (fichier Individus)", fint(ind_res.get("n_persons", 0))],
                ["Identifiant ménage unique", "oui" if hh_res["id_unique"] else "non"],
                ["Ménages sans individus / individus sans ménage",
                 f"{ind_res.get('households_without_individuals', '?')} / {ind_res.get('individuals_without_household', '?')}"],
                ["Taille du ménage = nombre de lignes Individus", f"{fnum(ind_res.get('size_matches_pct', 0), 2)} % des ménages"],
                ["Taille du ménage (min, max)", f"{hh_res['size']['min']:.0f}, {hh_res['size']['max']:.0f}"],
            ],
        ),
        "",
    ]

    w = hh_res["weights"]
    L += ["## Poids", ""]
    L += [
        md_table(
            ["Indicateur", "Valeur"],
            [
                [f"Somme de {W_HH} (ménages représentés)", fint(w["sum_w_hh"])],
                [f"Somme de {W_IND} (personnes représentées)", fint(w["sum_w_ind"])],
                [f"Somme de {W_HH} × taille", fint(w["sum_w_hh_times_size"])],
                [f"Rapport {W_IND} / ({W_HH} × taille) : min, moyenne, max",
                 f"{w['ratio_ind_over_hh_size_min']:.3f}, {w['ratio_ind_over_hh_size_mean']:.3f}, {w['ratio_ind_over_hh_size_max']:.3f}"],
            ],
        ),
        "",
        f"Les deux poids ne sont pas interchangeables : {W_IND} n'est pas égal à {W_HH} × taille.",
        "",
    ]

    d = hh_res["dam"]
    L += ["## Consommation", ""]
    L += [
        f"- {DAM} (MAD par an, non pondéré) : min {fint(d['min'])}, médiane {fint(d['median'])}, max {fint(d['max'])}.",
        f"- Écart maximal entre {DAP} et {DAM}/taille : {hh_res['dap_equals_dam_over_size_max_gap']:.6f}.",
        "",
    ]

    L += ["## Chiffres de contrôle de la note technique", ""]
    nc = hh_res["note_check"]
    rows = []
    labels = {
        "n_households": "Nombre de ménages",
        "sum_w_hh": f"Somme de {W_HH}",
        "mean_dam_w_hh": f"{DAM} moyenne, pondérée par {W_HH}",
        "mean_dap_w_ind": f"{DAP} moyenne, pondérée par {W_IND}",
    }
    for k, lab in labels.items():
        fmt = fint if k in ("n_households", "sum_w_hh") else fnum
        rows.append([lab, fmt(nc[k]["note"]), fmt(nc[k]["data"]), "oui" if nc[k]["ok"] else "non"])
    L += [md_table(["Contrôle", "Note", "Données", "Reproduit"], rows), ""]
    L += [
        "Pondération inverse (non publiée dans la note) :",
        f"- {DAM} moyenne pondérée par {W_IND} : {fnum(nc['mean_dam_w_ind_alt']['data'])}",
        f"- {DAP} moyenne pondérée par {W_HH} : {fnum(nc['mean_dap_w_hh_alt']['data'])}",
        "",
    ]

    p = hh_res["poverty"]
    L += ["## Indicateurs HCP de pauvreté (non documentés dans la note technique)", ""]
    L += [
        md_table(
            ["Indicateur", "Valeur"],
            [
                [f"Ménages `{POOR}`", fint(p["n_poor"])],
                [f"Ménages `{VULN}`", fint(p["n_vulnerable"])],
                ["Ménages à la fois pauvres et vulnérables", fint(p["n_poor_and_vulnerable"])],
                [f"Taux `{POOR}`, pondéré par personne ({W_IND})", f"{p['poor_pct_w_ind']:.2f} %"],
                [f"Taux `{POOR}`, pondéré par ménage ({W_HH})", f"{p['poor_pct_w_hh']:.2f} %"],
                [f"Taux `{VULN}`, pondéré par personne", f"{p['vulnerable_pct_w_ind']:.2f} %"],
            ],
        ),
        "",
        "Coupure observée sur la dépense par personne (MAD par an). Ceci est une observation "
        "sur les données, pas un seuil officiel.",
        "",
        md_table(
            ["Milieu", "DAP max des pauvres", "DAP min des non-pauvres"],
            [[m, fint(c["poor_max_dap"]), fint(c["nonpoor_min_dap"])] for m, c in hh_res["implied_cut_by_milieu"].items()],
        ),
        "",
    ]

    def table_group(title: str, rows_: list[dict]) -> list[str]:
        t = md_table(
            ["Code", "Modalité", "Ménages (non pondéré)", "Ménages représentés", f"Taux `{POOR}` (personnes)", "Effectif faible"],
            [
                [f"{r['code']:.0f}", r["label"], fint(r["n_households"]), fint(r["sum_w_hh"]),
                 f"{r['poor_pct_w_ind']:.2f} %", "oui" if r["small_cell"] else ""]
                for r in rows_
            ],
        )
        return [f"## {title}", "", t, ""]

    L += table_group("Milieu de résidence", hh_res["milieu"])
    L += table_group(f"Régions (seuil d'effectif faible provisoire : {hh_res['min_cell']} ménages, voir D12)", hh_res["region"])

    if "age" in ind_res:
        a = ind_res["age"]
        L += ["## Âges et enfants (fichier Individus, non pondéré)", ""]
        L += [
            f"- Âge : min {a['min']:.0f}, max {a['max']:.0f}, manquants {a['n_missing']}.",
            f"- Personnes de moins de 15 ans : {fint(a['n_under_15'])} ; de moins de 18 ans : {fint(a['n_under_18'])} (seuil de `children_count` en attente, voir D8).",
            "",
        ]

    if warnings:
        L += ["## Avertissements", *[f"- {x}" for x in warnings], ""]
    return "\n".join(L)


# =========================================================================================
# Programme principal
# =========================================================================================
def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(f"Non sérialisable : {type(o)}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Inspection reproductible de l'ENCDM 2014 (HCP).")
    ap.add_argument("--input-dir", type=Path, default=DEFAULT_DIR, help="Dossier des fichiers SAV.")
    ap.add_argument("--household-file", default=DEFAULT_HH_FILE, help="Nom du fichier Ménage.")
    ap.add_argument("--individual-file", default=DEFAULT_IND_FILE, help="Nom du fichier Individus.")
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUT, help="Dossier du rapport.")
    ap.add_argument("--min-cell", type=int, default=500,
                    help="Effectif non pondéré en dessous duquel un groupe est signalé (provisoire, D12).")
    args = ap.parse_args(argv)

    hh_path = args.input_dir / args.household_file
    ind_path = args.input_dir / args.individual_file
    for p in (hh_path, ind_path):
        if not p.exists():
            print(f"Fichier introuvable : {p}\nVoir data/raw/README.md pour l'emplacement attendu.", file=sys.stderr)
            return 2

    hh, hh_meta = read_sav(hh_path)
    ind, _ = read_sav(ind_path)
    hh_res = check_households(hh, hh_meta, args.min_cell)
    ind_res = check_individuals(ind, hh) if "n_households" in hh_res else {"errors": [], "warnings": []}

    files = {"household": hh_path.name, "individual": ind_path.name}
    report_md = build_markdown(hh_res, ind_res, files)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "encdm_2014_inspection.md").write_text(report_md, encoding="utf-8")
    payload = {"files": files, "households": hh_res, "individuals": ind_res}
    (args.output_dir / "encdm_2014_inspection.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8"
    )

    errors = hh_res.get("errors", []) + ind_res.get("errors", [])
    warnings = hh_res.get("warnings", []) + ind_res.get("warnings", [])
    print(f"Inspection terminée : {len(errors)} erreur(s), {len(warnings)} avertissement(s).")
    for e in errors:
        print(f"  ERREUR : {e}")
    for w in warnings:
        print(f"  Avertissement : {w}")
    print(f"Rapport : {args.output_dir / 'encdm_2014_inspection.md'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
