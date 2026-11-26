"""Tests de contrat et de bout en bout de l'export (B8)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analysis import export as ex
from src.analysis import metrics as m
from src.analysis import subgroups as sg

POP_MOCK = Path("data/mock/population_mock.csv")
SIM_MOCK = Path("data/mock/simulation_results_mock.csv")
pytestmark = pytest.mark.skipif(not (POP_MOCK.exists() and SIM_MOCK.exists()), reason="mock absente")


@pytest.fixture(scope="module")
def mock_inputs():
    return ex._read(POP_MOCK), ex._read(SIM_MOCK)


@pytest.fixture(scope="module")
def outputs(mock_inputs):
    pop, sim = mock_inputs
    return ex.build_outputs(sim, pop, None, annual_budget=4000.0 * 12, budget_basis="sample")


def test_columns_match_documented_schemas(outputs):
    scenario, groups = outputs
    assert list(scenario.columns) == m.LONG_COLUMNS
    assert list(groups.columns) == sg.GROUP_COLUMNS


def test_value_types_and_no_infinite_values(outputs):
    scenario, groups = outputs
    for df in (scenario, groups):
        assert pd.api.types.is_float_dtype(df["value"])
        assert pd.api.types.is_float_dtype(df["denominator"])
        assert not np.isinf(df["value"].to_numpy(dtype=float)).any()
        for col in df.columns.difference(["value", "denominator"]):
            assert df[col].map(lambda x: isinstance(x, str)).all(), col


def test_keys_are_unique(outputs):
    scenario, groups = outputs
    assert not scenario.duplicated(["run_id", "scenario_id", "metric", "weighting_basis"]).any()
    assert not groups.duplicated(
        ["run_id", "scenario_id", "subgroup_dimension", "subgroup_value", "metric", "weighting_basis"]
    ).any()


def test_every_metric_has_a_definition(outputs):
    scenario, groups = outputs
    for metric in set(scenario["metric"]) | set(groups["metric"]):
        assert ex.is_defined(metric), metric
    assert not ex.is_defined("metric_inconnue")
    assert not ex.is_defined("metric_inconnue_change_vs_S0")


def test_runs_scenarios_and_baseline_present(outputs, mock_inputs):
    scenario, groups = outputs
    _, sim = mock_inputs
    assert {"baseline", "S0", "S1", "S2", "S3"} == set(scenario["scenario_id"])
    assert set(sim["run_id"]) <= set(scenario["run_id"])
    assert {"S1", "S2", "S3"} == set(scenario[scenario.metric == "fiscal_cost_annual"]["scenario_id"])
    assert "budget_utilization" in set(scenario["metric"])


def test_budget_breach_stops_the_export(mock_inputs):
    pop, sim = mock_inputs
    with pytest.raises(ValueError, match="Budget dépassé"):
        ex.build_outputs(sim, pop, None, annual_budget=40_000.0, budget_basis="sample")


def test_invalid_simulation_stops_the_export(mock_inputs):
    pop, sim = mock_inputs
    with pytest.raises(ValueError):
        ex.build_outputs(sim.drop(columns=["seed"]), pop)
    with pytest.raises(ValueError):
        ex.build_outputs(pd.concat([sim, sim.iloc[:1]]), pop)


def test_write_roundtrip_preserves_columns_and_values(outputs, tmp_path):
    scenario, groups = outputs
    paths = ex.write_outputs(scenario, groups, tmp_path, "_mock", {"mode": "test"})
    s2 = pd.read_csv(paths["scenario_metrics"], dtype={"run_id": str})
    g2 = pd.read_csv(paths["group_impacts"], dtype={"run_id": str})
    assert list(s2.columns) == m.LONG_COLUMNS and list(g2.columns) == sg.GROUP_COLUMNS
    assert len(s2) == len(scenario) and len(g2) == len(groups)
    np.testing.assert_allclose(s2["value"].to_numpy(dtype=float), scenario["value"].to_numpy(dtype=float), equal_nan=True)
    defs = pd.read_csv(paths["metric_definitions"])
    assert list(defs.columns) == ["metric", "appears_in", "unit", "definition"]
    assert defs["definition"].str.len().gt(10).all()
    meta = json.loads(paths["analysis_metadata"].read_text(encoding="utf-8"))
    assert meta["outputs"]["scenario_metrics_rows"] == len(scenario)


def test_main_end_to_end_in_mock_mode(tmp_path, capsys):
    ex.main(["--mock", "--out-dir", str(tmp_path)])
    for name in ["scenario_metrics_mock.csv", "group_impacts_mock.csv", "metric_definitions_mock.csv", "analysis_metadata_mock.json"]:
        assert (tmp_path / name).exists(), name
    meta = json.loads((tmp_path / "analysis_metadata_mock.json").read_text(encoding="utf-8"))
    assert "mock" in meta["mode"] and meta["budget_basis"] == "sample"
    assert len(meta["inputs"]["population"]["sha256"]) == 64
    assert meta["person_basis"].startswith("approximation")
    assert "scenario_metrics" in capsys.readouterr().out


def test_main_stops_when_files_are_missing(tmp_path):
    with pytest.raises(SystemExit):
        ex.main(["--simulation", str(tmp_path / "absent.csv"), "--out-dir", str(tmp_path)])
