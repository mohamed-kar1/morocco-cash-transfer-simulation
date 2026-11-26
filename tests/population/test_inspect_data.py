"""Tests de src/population/inspect_data.py sur de petits cas calculés à la main."""

from types import SimpleNamespace

import pandas as pd
import pytest

from src.population import inspect_data as m

META = SimpleNamespace(
    variable_value_labels={
        m.MILIEU: {1.0: "Urbain", 2.0: "Rural"},
        m.REGION: {1.0: "Région A", 2.0: "Région B"},
    }
)


def make_households() -> pd.DataFrame:
    """4 ménages : tailles 3, 2, 1, 4 (texte avec espaces, comme dans le fichier SAV)."""
    size_txt = ["3 ", " 2", "1", "4  "]
    dam = [12000.0, 24000.0, 36000.0, 48000.0]
    size = [3, 2, 1, 4]
    return pd.DataFrame(
        {
            m.HH_ID: [1.0, 2.0, 3.0, 4.0],
            m.W_HH: [10.0, 20.0, 30.0, 40.0],
            m.W_IND: [30.0, 40.0, 60.0, 70.0],
            m.MILIEU: [1.0, 1.0, 2.0, 2.0],
            m.REGION: [1.0, 1.0, 2.0, 2.0],
            m.SIZE: size_txt,
            m.DAM: dam,
            m.DAP: [d / s for d, s in zip(dam, size)],
            m.POOR: [1, 0, 0, 0],
            m.VULN: [0, 1, 0, 0],
        }
    )


def make_individuals(sizes=(3, 2, 1, 4)) -> pd.DataFrame:
    ids = [i + 1.0 for i, s in enumerate(sizes) for _ in range(s)]
    return pd.DataFrame({m.HH_ID: ids, m.AGE: [5.0 + k for k in range(len(ids))]})


def test_valid_households_have_no_errors():
    res = m.check_households(make_households(), META, min_cell=3)
    assert res["errors"] == []
    assert res["n_households"] == 4
    assert res["id_unique"] is True


def test_duplicate_household_id_is_an_error():
    hh = make_households()
    hh.loc[1, m.HH_ID] = 1.0
    res = m.check_households(hh, META, min_cell=3)
    assert any("unique" in e for e in res["errors"])


def test_non_positive_weight_is_an_error():
    hh = make_households()
    hh.loc[0, m.W_HH] = 0.0
    res = m.check_households(hh, META, min_cell=3)
    assert any(m.W_HH in e for e in res["errors"])


def test_non_positive_dam_is_an_error():
    hh = make_households()
    hh.loc[2, m.DAM] = -1.0
    res = m.check_households(hh, META, min_cell=3)
    assert any(m.DAM in e for e in res["errors"])


def test_missing_required_column_is_reported():
    hh = make_households().drop(columns=[m.REGION])
    res = m.check_households(hh, META, min_cell=3)
    assert any("Colonnes manquantes" in e for e in res["errors"])


def test_to_size_handles_padded_and_invalid_text():
    out = m.to_size(pd.Series(["3 ", " 2", "abc"]))
    assert out.iloc[0] == 3 and out.iloc[1] == 2
    assert pd.isna(out.iloc[2])


def test_weighted_share_hand_calculated():
    # un ménage pauvre sur deux, pondéré 2 contre 1 : part = 2 / 3
    share = m.weighted_share(pd.Series([1, 0]), pd.Series([2.0, 1.0]))
    assert share == pytest.approx(100 * 2 / 3)


def test_poverty_rates_by_both_weights():
    res = m.check_households(make_households(), META, min_cell=3)
    # seul le ménage 1 est pauvre : 30 / 200 par personne, 10 / 100 par ménage
    assert res["poverty"]["poor_pct_w_ind"] == pytest.approx(15.0)
    assert res["poverty"]["poor_pct_w_hh"] == pytest.approx(10.0)
    assert res["poverty"]["n_poor_and_vulnerable"] == 0


def test_implied_poverty_cut():
    dap = pd.Series([4000.0, 12000.0, 36000.0, 12000.0])
    poor = pd.Series([1, 0, 0, 0])
    cut = m.implied_poverty_cut(dap, poor)
    assert cut == {"poor_max_dap": 4000.0, "nonpoor_min_dap": 12000.0}


def test_dap_equals_dam_over_size():
    res = m.check_households(make_households(), META, min_cell=3)
    assert res["dap_equals_dam_over_size_max_gap"] == pytest.approx(0.0)


def test_small_cell_regions_are_flagged():
    res = m.check_households(make_households(), META, min_cell=3)
    assert all(r["small_cell"] for r in res["region"])  # 2 ménages par région < 3
    res = m.check_households(make_households(), META, min_cell=2)
    assert not any(r["small_cell"] for r in res["region"])


def test_individuals_consistent_with_households():
    hh, ind = make_households(), make_individuals()
    res = m.check_individuals(ind, hh)
    assert res["errors"] == []
    assert res["size_matches_pct"] == pytest.approx(100.0)
    assert res["n_persons"] == 10
    assert res["age"]["n_under_15"] == 10


def test_size_mismatch_between_files_is_an_error():
    hh = make_households()
    ind = make_individuals(sizes=(3, 2, 1, 3))  # le ménage 4 a 3 lignes au lieu de 4
    res = m.check_individuals(ind, hh)
    assert any("taille" in e for e in res["errors"])


def test_unmatched_ids_are_an_error():
    hh = make_households()
    ind = make_individuals()
    ind.loc[0, m.HH_ID] = 99.0
    res = m.check_individuals(ind, hh)
    assert any("non appariés" in e for e in res["errors"])


def test_markdown_report_builds_and_mentions_status():
    hh, ind = make_households(), make_individuals()
    report = m.build_markdown(
        m.check_households(hh, META, min_cell=3),
        m.check_individuals(ind, hh),
        {"household": "hh.sav", "individual": "ind.sav"},
    )
    assert report.startswith("# Rapport d'inspection")
    assert "Statut : **OK**" in report
