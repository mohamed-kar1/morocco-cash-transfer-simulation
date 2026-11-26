"""Compare les marges de l'ENCDM 2014 (pondérée) à celles du RGPH 2014 (ménages).

Objectif (décision D1) : savoir si recalibrer les poids de l'ENCDM par IPF apporterait
quelque chose. On compare les répartitions par milieu, par région et par taille du
ménage. Le script ne modifie aucune donnée brute et n'écrit que des agrégats.

Usage :
    python -m src.population.compare_rgph

Code de sortie : 0 si le rapport est écrit, 2 si un fichier manque.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

import pandas as pd
import pyreadstat

ENC_FILE = Path("data/raw/encdm_2014/Ménage_ENCDM_2014_en_format_SAV.sav")
RGPH_DIR = Path("data/raw/rgph_2014")
OUT = Path("outputs/inspection/rgph_vs_encdm.md")
ENC_COLS = ["Milieu", "Région_12", "Taille_ménage", "coef_ménage"]
RGPH_COLS = ["REG", "MIL", "TAILLE", "MEN.TYPE", "PDS"]
SIZE_CAP = 7  # tailles regroupées : 1, 2, ..., 6, 7 et plus
GAP_FLAG_PP = 2.0  # valeur de travail : écart signalé au-dessus de 2 points (D1)


def norm(x: object) -> str:
    s = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode()
    return " ".join(s.lower().replace("-", " ").replace("'", " ").split())


def labelled(df: pd.DataFrame, meta, col: str) -> pd.Series:
    labels = getattr(meta, "variable_value_labels", {}).get(col, {})
    codes = pd.to_numeric(df[col], errors="coerce")
    return codes.map(lambda v: labels.get(v, str(v) if pd.notna(v) else "manquant"))


def size_group(raw: pd.Series) -> pd.Series:
    n = pd.to_numeric(raw.astype(str).str.strip(), errors="coerce")
    return n.clip(upper=SIZE_CAP).map(
        lambda v: "manquant" if pd.isna(v) else (f"{int(v)}+" if v >= SIZE_CAP else str(int(v)))
    )


def shares(group: pd.Series, w: pd.Series) -> pd.Series:
    t = w.groupby(group).sum()
    return t / t.sum()


def find_rgph_household_file(folder: Path) -> Path | None:
    hits = sorted(p for p in folder.glob("*.sav") if "nage" in p.name)
    return hits[0] if hits else None


def compare(enc: pd.Series, rg: pd.Series, enc_label: str = "ENCDM", rg_label: str = "RGPH"):
    """Joint les deux répartitions par libellé normalisé ; renvoie (tableau, non appariés)."""
    e = enc.rename(index=norm).groupby(level=0).sum()
    r = rg.rename(index=norm).groupby(level=0).sum()
    keys = sorted(set(e.index) | set(r.index))
    tab = pd.DataFrame({f"{enc_label} (%)": e.reindex(keys) * 100, f"{rg_label} (%)": r.reindex(keys) * 100})
    tab["Écart (points)"] = tab.iloc[:, 0] - tab.iloc[:, 1]
    unmatched = [k for k in keys if k not in e.index or k not in r.index]
    return tab, unmatched


def md_table(tab: pd.DataFrame) -> str:
    lines = ["| Modalité | " + " | ".join(tab.columns) + " |", "|---|" + "---|" * len(tab.columns)]
    for k, row in tab.iterrows():
        cells = ["" if pd.isna(v) else f"{v:.2f}" for v in row]
        flag = " (écart)" if pd.notna(row.iloc[-1]) and abs(row.iloc[-1]) > GAP_FLAG_PP else ""
        lines.append(f"| {k}{flag} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def run(enc_file: Path, rgph_file: Path, out: Path) -> dict:
    enc, em = pyreadstat.read_sav(str(enc_file), usecols=ENC_COLS, apply_value_formats=False)
    rg, rm = pyreadstat.read_sav(str(rgph_file), usecols=RGPH_COLS, apply_value_formats=False)

    notes: list[str] = []
    rg["_type"] = labelled(rg, rm, "MEN.TYPE")
    types = rg["_type"].value_counts()
    ordinary = rg["_type"].map(lambda t: "ordinaire" in norm(t) and "collectif" not in norm(t))
    if ordinary.any():
        notes.append("Ménages RGPH filtrés sur le type « ordinaire » (l'ENCDM ne couvre que les ménages ordinaires).")
        rg = rg[ordinary]
    else:
        notes.append("MEN.TYPE décrit la composition familiale (aucun type « ordinaire » ou « collectif ») : aucun filtre appliqué, la comparaison porte sur tous les ménages du fichier.")

    rg_w, enc_w = rg["PDS"].astype(float), enc["coef_ménage"].astype(float)
    result: dict = {"rg_n": len(rg), "rg_w": rg_w.sum(), "enc_n": len(enc), "enc_w": enc_w.sum()}

    enc["_milieu"] = labelled(enc, em, "Milieu")
    enc["_reg"] = labelled(enc, em, "Région_12")
    rg["_milieu"] = labelled(rg, rm, "MIL")
    rg["_reg"] = labelled(rg, rm, "REG")
    enc["_size"] = size_group(enc["Taille_ménage"])
    rg["_size"] = size_group(rg["TAILLE"])

    sections = []
    for title, ecol, rcol in [("Milieu de résidence", "_milieu", "_milieu"),
                              ("Région", "_reg", "_reg"),
                              ("Taille du ménage", "_size", "_size")]:
        tab, unmatched = compare(shares(enc[ecol], enc_w), shares(rg[rcol], rg_w))
        gap = tab["Écart (points)"].abs().max()
        result[title] = (None if pd.isna(gap) else float(gap), unmatched)
        text = f"## {title}\n\n" + md_table(tab)
        if unmatched:
            text += "\n\nModalités sans équivalent dans l'autre source (libellés différents ou absentes) : " + ", ".join(unmatched)
        sections.append(text)

    head = [
        "# Comparaison ENCDM 2014 et RGPH 2014 (ménages)",
        "",
        "Rapport d'agrégats uniquement. Les parts sont pondérées (`coef_ménage` pour l'ENCDM, `PDS` pour le RGPH).",
        "",
        "| | ENCDM 2014 | RGPH 2014 (fichier à 10 %) |",
        "|---|---|---|",
        f"| Ménages (non pondéré) | {result['enc_n']:,} | {result['rg_n']:,} |".replace(",", " "),
        f"| Ménages représentés (somme des poids) | {result['enc_w']:,.0f} | {result['rg_w']:,.0f} |".replace(",", " "),
        "",
        "Types de ménage du RGPH (non pondéré) : " + ", ".join(f"{k} : {v}" for k, v in types.items()),
        "",
        *[f"- {n}" for n in notes],
        f"- Un écart supérieur à {GAP_FLAG_PP:.0f} points est signalé. Cette valeur est un seuil de travail (D1).",
        "",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(head) + "\n" + "\n\n".join(sections) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--encdm-file", type=Path, default=ENC_FILE)
    ap.add_argument("--rgph-file", type=Path, default=None, help="Fichier Ménage du RGPH (SAV).")
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args(argv)

    rgph = args.rgph_file or find_rgph_household_file(RGPH_DIR)
    for p in (args.encdm_file, rgph):
        if p is None or not Path(p).exists():
            print(f"Fichier introuvable : {p}\nVoir data/raw/README.md pour l'emplacement attendu.", file=sys.stderr)
            return 2

    res = run(args.encdm_file, Path(rgph), args.output)
    print(f"Ménages représentés : ENCDM {res['enc_w']:,.0f} | RGPH {res['rg_w']:,.0f}".replace(",", " "))
    for k in ("Milieu de résidence", "Région", "Taille du ménage"):
        gap, unmatched = res[k]
        extra = f" ; modalités non appariées : {len(unmatched)}" if unmatched else ""
        print(f"{k} : écart maximal {gap:.2f} points{extra}" if gap is not None else f"{k} : non comparable{extra}")
    print(f"Rapport : {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
