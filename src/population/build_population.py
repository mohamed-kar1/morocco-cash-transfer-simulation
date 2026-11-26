"""Construction de data/processed/population.csv à partir de l'ENCDM 2014.

Règles (voir docs/pending_decisions.md) :
- D2 : equivalence_factor = taille du ménage
- D3 : DAM total
- D4 : baseline_consumption = DAM / 12 (MAD courants 2014)
- D6 : eligible_baseline = Pauvre ou Vulnérable (indicateurs HCP)
- D7 : household_weight = coef_ménage
- D8 : children_count = personnes de moins de 15 ans (fichier Individus)

Usage : python -m src.population.build_population
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW = Path("data/raw/encdm_2014")
MENAGE_SAV = RAW / "Ménage_ENCDM_2014_en_format_SAV.sav"
INDIV_SAV = RAW / "Individus__ENCDM_2014_en_format_SAV.sav"
OUT_CSV = Path("data/processed/population.csv")
PERSON_WEIGHTS_CSV = Path("data/processed/person_weights.csv")  # fichier interne P1 (D14), hors contrat partagé
LOG_MD = Path("outputs/build/population_build_log.md")

COLUMNS = [
    "household_id",
    "household_weight",
    "region",
    "urban_rural",
    "household_size",
    "children_count",
    "baseline_consumption",
    "equivalence_factor",
    "equiv_consumption",
    "eligible_baseline",
]

CHILD_AGE_LIMIT = 15  # D8 : enfant = moins de 15 ans
MONTHS = 12  # D4
URBAN_RURAL = {1: "urbain", 2: "rural"}  # codes de la variable Milieu

# Chiffres de contrôle (note technique HCP et tests précédents)
EXPECTED_ROWS = 15_970
EXPECTED_WEIGHT_SUM = 7_190_456
EXPECTED_POOR = 499  # ménages Pauvre (drapeau HCP)
EXPECTED_ELIGIBLE = 1_998  # Pauvre ou Vulnérable
EXPECTED_CHILDREN = 20_312  # personnes de moins de 15 ans (rapport d'inspection)
EXPECTED_PERSON_WEIGHT_SUM = 33_579_281  # somme de coef_indiv (rapport d'inspection)


class BuildLog:
    """Journal de construction : nombre de lignes avant et après chaque opération (A4)."""

    def __init__(self) -> None:
        self.steps: list[dict] = []

    def step(self, operation: str, before: int, after: int, note: str = "") -> None:
        before, after = int(before), int(after)
        self.steps.append(
            {"operation": operation, "avant": before, "apres": after, "exclues": before - after, "note": note}
        )

    def to_markdown(self, summary: dict | None = None) -> str:
        lines = [
            "# Journal de construction de `population.csv`",
            "",
            "Agrégats uniquement. « Exclues » = lignes retirées par l'opération (0 si aucune).",
            "",
            "| # | Opération | Lignes avant | Lignes après | Exclues | Remarque |",
            "|---|---|---|---|---|---|",
        ]
        for i, st in enumerate(self.steps, 1):
            n = {k: f"{st[k]:,}".replace(",", " ") for k in ("avant", "apres", "exclues")}
            lines.append(f"| {i} | {st['operation']} | {n['avant']} | {n['apres']} | {n['exclues']} | {st['note']} |")
        if summary:
            lines += ["", "## Totaux du fichier produit", ""]
            lines += [f"- {k} : {v}" for k, v in summary.items()]
        return "\n".join(lines) + "\n"

    def write(self, path: Path, summary: dict | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(summary), encoding="utf-8")


def _key(series: pd.Series) -> pd.Series:
    """Identifiant ménage comparable entre les deux fichiers."""
    num = pd.to_numeric(series, errors="coerce")
    if num.notna().all():
        return num.astype("int64")
    return series.astype(str).str.strip()


def _to_int(series: pd.Series, name: str) -> pd.Series:
    num = pd.to_numeric(series.astype(str).str.strip(), errors="coerce")
    if num.isna().any():
        raise ValueError(f"{name} : {int(num.isna().sum())} valeur(s) non numérique(s).")
    return num.astype("int64")


def flag_yes(series: pd.Series) -> pd.Series:
    """Indicateur booléen : code 1 = oui (vérifié ensuite par les chiffres de contrôle)."""
    return pd.to_numeric(series.astype(str).str.strip(), errors="coerce").eq(1)


def count_children(indiv: pd.DataFrame) -> pd.Series:
    """Nombre de personnes de moins de 15 ans par ménage (index = household_id)."""
    ids = _key(indiv["N_ménage"])
    age = pd.to_numeric(indiv["Age"].astype(str).str.strip(), errors="coerce")
    if age.isna().any():
        raise ValueError(f"Age : {int(age.isna().sum())} valeur(s) manquante(s) ou non numérique(s).")
    return (age < CHILD_AGE_LIMIT).groupby(ids).sum().astype("int64")


def build_population(
    menage: pd.DataFrame,
    indiv: pd.DataFrame,
    region_labels: dict | None = None,
    log: BuildLog | None = None,
) -> pd.DataFrame:
    hid = _key(menage["N_ménage"])
    size = _to_int(menage["Taille_ménage"], "Taille_ménage")
    if log:
        log.step("Conversion de Taille_ménage (texte vers entier)", len(menage), len(size), "toute valeur non numérique arrête le script")

    if region_labels:
        region = menage["Région_12"].map(region_labels)
    else:
        region = menage["Région_12"].astype(str).str.strip()
    if region.isna().any():
        raise ValueError("Région_12 : valeurs sans libellé.")
    if log:
        log.step("Recodage de Région_12 en libellés", len(menage), len(region), f"{region.nunique()} régions")

    urban_rural = pd.to_numeric(menage["Milieu"], errors="coerce").map(URBAN_RURAL)
    if urban_rural.isna().any():
        raise ValueError("Milieu : code inattendu (attendu 1 = urbain, 2 = rural).")
    if log:
        log.step("Recodage de Milieu (1 = urbain, 2 = rural)", len(menage), len(urban_rural))

    children = count_children(indiv)
    if log:
        n_without = int(hid.map(children).isna().sum())
        log.step(
            "Comptage des enfants de moins de 15 ans (fichier Individus)",
            len(indiv),
            len(indiv),
            f"{n_without} ménage(s) sans individu : enfants = 0",
        )

    baseline = menage["DAM"].astype(float) / MONTHS
    equiv_factor = size.astype(float)

    pop = pd.DataFrame(
        {
            "household_id": hid.astype(str).to_numpy(),
            "household_weight": menage["coef_ménage"].astype(float).to_numpy(),
            "region": region.to_numpy(),
            "urban_rural": urban_rural.to_numpy(),
            "household_size": size.to_numpy(),
            "children_count": hid.map(children).fillna(0).astype("int64").to_numpy(),
            "baseline_consumption": baseline.to_numpy(),
            "equivalence_factor": equiv_factor.to_numpy(),
            "equiv_consumption": (baseline / equiv_factor).to_numpy(),
            "eligible_baseline": (
                (flag_yes(menage["Pauvre"]) | flag_yes(menage["Vulnérable"])).astype(int).to_numpy()
            ),
        }
    )
    if log:
        log.step("Calcul des 10 colonnes du contrat (D2 à D8)", len(menage), len(pop), "aucun ménage retiré")
    return pop[COLUMNS]


def build_person_weights(menage: pd.DataFrame) -> pd.DataFrame:
    """Poids personne (coef_indiv) par ménage, pour les mesures par personne (D7, D14).

    Fichier interne de l'analyse : il ne fait pas partie du contrat population.csv.
    """
    return pd.DataFrame(
        {
            "household_id": _key(menage["N_ménage"]).astype(str).to_numpy(),
            "person_weight": menage["coef_indiv"].astype(float).to_numpy(),
        }
    )


def validate_person_weights(pw: pd.DataFrame, pop: pd.DataFrame) -> None:
    if list(pw.columns) != ["household_id", "person_weight"]:
        raise ValueError(f"person_weights : colonnes inattendues {list(pw.columns)}")
    if not pw["household_id"].is_unique or set(pw["household_id"]) != set(pop["household_id"]):
        raise ValueError("person_weights : les household_id ne correspondent pas à population.csv.")
    w = pw["person_weight"]
    if w.isna().any() or not (w > 0).all() or not w.map(lambda x: x < float("inf")).all():
        raise ValueError("person_weights : poids manquants, nuls, négatifs ou infinis.")


def validate_contract(pop: pd.DataFrame) -> None:
    """Contrôles génériques du schéma (valables aussi pour la mock)."""
    if list(pop.columns) != COLUMNS:
        raise ValueError(f"Colonnes inattendues : {list(pop.columns)}")
    if pop.isna().any().any():
        raise ValueError("Valeurs manquantes : le contrat n'en autorise aucune.")
    if not pop["household_id"].is_unique:
        raise ValueError("household_id non unique.")
    if not (pop["household_weight"] > 0).all():
        raise ValueError("household_weight doit être strictement positif.")
    if not (pop["household_size"] >= 1).all():
        raise ValueError("household_size doit être >= 1.")
    if not pop["children_count"].between(0, pop["household_size"]).all():
        raise ValueError("children_count doit être entre 0 et household_size.")
    if not (pop["baseline_consumption"] > 0).all():
        raise ValueError("baseline_consumption doit être positif.")
    if not ((pop["equiv_consumption"] - pop["baseline_consumption"] / pop["equivalence_factor"]).abs() < 0.01).all():
        raise ValueError("equiv_consumption != baseline_consumption / equivalence_factor.")
    if not set(pop["urban_rural"]) <= set(URBAN_RURAL.values()):
        raise ValueError("urban_rural : modalités inattendues.")
    if not set(pop["eligible_baseline"]) <= {0, 1}:
        raise ValueError("eligible_baseline doit valoir 0 ou 1.")


def validate_against_survey(pop: pd.DataFrame, n_poor: int, n_size_mismatch: int = 0) -> None:
    """Contrôles sur les vraies données (chiffres de la note technique et du registre)."""
    problems = []
    if len(pop) != EXPECTED_ROWS:
        problems.append(f"lignes : {len(pop)} au lieu de {EXPECTED_ROWS}")
    wsum = pop["household_weight"].sum()
    if abs(wsum - EXPECTED_WEIGHT_SUM) > 1:
        problems.append(f"somme des poids : {wsum:,.0f} au lieu de {EXPECTED_WEIGHT_SUM:,}")
    if n_size_mismatch != 0:
        problems.append(f"{n_size_mismatch} ménage(s) dont la taille != nombre d'individus")
    n_children = int(pop["children_count"].sum())
    if n_children != EXPECTED_CHILDREN:
        problems.append(f"enfants de moins de 15 ans : {n_children} au lieu de {EXPECTED_CHILDREN}")
    if pop["region"].nunique() != 12:
        problems.append(f"régions : {pop['region'].nunique()} au lieu de 12")
    if n_poor != EXPECTED_POOR:
        problems.append(f"ménages Pauvre : {n_poor} au lieu de {EXPECTED_POOR} (codage de Pauvre ?)")
    n_elig = int(pop["eligible_baseline"].sum())
    if n_elig != EXPECTED_ELIGIBLE:
        problems.append(f"éligibles : {n_elig} au lieu de {EXPECTED_ELIGIBLE} (codage de Vulnérable ?)")
    if problems:
        raise ValueError("Contrôles échoués :\n- " + "\n- ".join(problems))


def main() -> None:
    import pyreadstat

    for path in (MENAGE_SAV, INDIV_SAV):
        if not path.exists():
            raise SystemExit(f"Fichier introuvable : {path}\nVoir data/raw/README.md.")

    log = BuildLog()
    menage, meta = pyreadstat.read_sav(
        str(MENAGE_SAV),
        usecols=["N_ménage", "coef_ménage", "coef_indiv", "Milieu", "Région_12", "Taille_ménage", "Pauvre", "Vulnérable", "DAM"],
    )
    indiv, _ = pyreadstat.read_sav(str(INDIV_SAV), usecols=["N_ménage", "Age"])
    log.step("Lecture du fichier Ménage (9 variables utiles)", len(menage), len(menage), MENAGE_SAV.name)
    log.step("Lecture du fichier Individus (2 variables utiles)", len(indiv), len(indiv), INDIV_SAV.name)

    labels = meta.variable_value_labels.get("Région_12")
    pop = build_population(menage, indiv, labels, log)

    # Diagnostics (non bloquants) : cohérence taille du ménage / nombre d'individus
    n_indiv = _key(indiv["N_ménage"]).value_counts()
    mismatch = int((_key(menage["N_ménage"]).map(n_indiv).fillna(0).to_numpy() != pop["household_size"].to_numpy()).sum())
    print(f"Ménages dont la taille != nombre d'individus : {mismatch}")
    print(f"Enfants de moins de 15 ans : {int(pop['children_count'].sum())}")
    print("Pauvre (codes) :", menage["Pauvre"].value_counts(dropna=False).to_dict())
    print("Vulnérable (codes) :", menage["Vulnérable"].value_counts(dropna=False).to_dict())

    validate_contract(pop)
    validate_against_survey(pop, int(flag_yes(menage["Pauvre"]).sum()), mismatch)
    pw = build_person_weights(menage)
    validate_person_weights(pw, pop)
    if abs(pw["person_weight"].sum() - EXPECTED_PERSON_WEIGHT_SUM) > 1:
        raise ValueError(
            f"Somme de coef_indiv : {pw['person_weight'].sum():,.0f} au lieu de {EXPECTED_PERSON_WEIGHT_SUM:,}"
        )
    log.step("Validation du contrat et des chiffres de contrôle", len(pop), len(pop), "lignes, poids, enfants, Pauvre, éligibles")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pop.to_csv(OUT_CSV, index=False, encoding="utf-8")
    log.step("Export de population.csv", len(pop), len(pop), str(OUT_CSV))
    pw.to_csv(PERSON_WEIGHTS_CSV, index=False, encoding="utf-8")
    log.step("Export de person_weights.csv (coef_indiv, fichier interne, D14)", len(pw), len(pw), str(PERSON_WEIGHTS_CSV))
    log.write(
        LOG_MD,
        {
            "Lignes": f"{len(pop):,}".replace(",", " "),
            "Somme de household_weight": f"{pop['household_weight'].sum():,.0f}".replace(",", " "),
            "Ménages Pauvre (drapeau HCP)": f"{int(flag_yes(menage['Pauvre']).sum()):,}".replace(",", " "),
            "Ménages éligibles (Pauvre ou Vulnérable)": f"{int(pop['eligible_baseline'].sum()):,}".replace(",", " "),
            "Enfants de moins de 15 ans": f"{int(pop['children_count'].sum()):,}".replace(",", " "),
            "Somme de coef_indiv (personnes représentées)": f"{pw['person_weight'].sum():,.0f}".replace(",", " "),
            "Ménages dont la taille != nombre d'individus": mismatch,
        },
    )
    print(f"Journal : {LOG_MD}")
    print(
        f"population.csv : {len(pop)} lignes, somme des poids {pop['household_weight'].sum():,.0f}, "
        f"{int(pop['eligible_baseline'].sum())} éligibles -> {OUT_CSV}"
    )


if __name__ == "__main__":
    main()