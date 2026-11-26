import pandas as pd
import pyreadstat

from src.population import compare_rgph as c


def test_norm_ignores_accents_case_and_hyphens():
    assert c.norm("Tanger-Tétouan - Al Hoceïma") == c.norm("tanger tetouan al hoceima")


def test_size_group_caps_and_handles_text():
    out = c.size_group(pd.Series([" 1 ", "3", "9", "x"]))
    assert list(out) == ["1", "3", "7+", "manquant"]


def test_compare_gap_and_unmatched():
    enc = pd.Series({"Urbain": 0.6, "Rural": 0.4})
    rg = pd.Series({"urbain": 0.5, "rural": 0.4, "autre": 0.1})
    tab, unmatched = c.compare(enc, rg)
    assert round(tab.loc["urbain", "Écart (points)"], 6) == 10.0
    assert unmatched == ["autre"]


def test_run_writes_report(tmp_path):
    enc = pd.DataFrame({"Milieu": [1.0, 2.0], "Région_12": [1.0, 1.0],
                        "Taille_ménage": [" 2 ", " 4 "], "coef_ménage": [100.0, 100.0]})
    pyreadstat.write_sav(enc, str(tmp_path / "e.sav"),
                         variable_value_labels={"Milieu": {1.0: "Urbain", 2.0: "Rural"},
                                                "Région_12": {1.0: "Oriental"}})
    rg = pd.DataFrame({"REG": [1.0] * 3, "MIL": [1.0, 2.0, 2.0], "TAILLE": [2.0, 4.0, 4.0],
                       "MEN.TYPE": [1.0, 1.0, 2.0], "PDS": [10.0] * 3})
    pyreadstat.write_sav(rg, str(tmp_path / "r.sav"),
                         variable_value_labels={"MIL": {1.0: "Urbain", 2.0: "Rural"},
                                                "REG": {1.0: "Oriental"},
                                                "MEN.TYPE": {1.0: "Ménage ordinaire", 2.0: "Ménage collectif"}})
    out = tmp_path / "rep.md"
    res = c.run(tmp_path / "e.sav", tmp_path / "r.sav", out)
    assert res["rg_n"] == 2  # le ménage collectif est exclu
    assert res["Milieu de résidence"][0] == 0.0
    assert "Comparaison ENCDM 2014 et RGPH 2014" in out.read_text(encoding="utf-8")
