import json
from pathlib import Path

import jsonschema
import numpy as np
import pandas as pd
import pytest

from scripts.data_audit import audit_dataframe, audit_file
from scripts.error_registry import query_errors, record_error, resolve
from scripts.problem_analysis import check_analysis
from scripts.solver_strategy import classify, portfolio_for
from scripts.validation_uq import calibration_curve, morris_screening, rolling_backtest

ROOT = Path(__file__).resolve().parents[2]


def test_data_audit_schema_and_missing_declared_column(tmp_path):
    data = tmp_path / 'small.csv'
    pd.DataFrame({'x': range(10), 'probability': [0, .1, .2, .3, .4, .5, .6, .7, .8, 2]}).to_csv(data, index=False)
    report = audit_file(data, target='missing_target')
    schema = json.loads((ROOT / '90_工具与配置/schemas/data-audit.schema.json').read_text(encoding='utf-8'))
    jsonschema.Draft202012Validator(schema).validate(report)
    codes = {item['code'] for item in report['findings']}
    assert {'SCHEMA_MISMATCH', 'IMPOSSIBLE_VALUE'} <= codes
    assert report['verdict'] == 'blocked'


def valid_analysis():
    return {'schema_version':'1.0','problem_id':'p','subproblems':[{'id':'s1','statement':'x','depends_on':[]}],
      'task_types':['optimization'],'variables':{'decision':[{'name':'x','meaning':'choice','unit':'1'}], 'state':[], 'exogenous':[]},
      'objectives':[{'id':'o','statement':'cost','sense':'minimize'}], 'constraints':[],
      'assumption_ledger':[], 'data_requirements':[], 'output_requirements':['answer'],
      'evaluation_metrics':[{'id':'m','definition':'cost','aligns_with':'o'}],
      'identifiability_risks':[], 'hidden_requirements':[], 'terminology':[]}


def test_problem_analysis_references_and_duplicate_ids():
    artifact = valid_analysis()
    assert check_analysis(artifact) == []
    artifact['subproblems'].append(dict(artifact['subproblems'][0]))
    assert 'subproblem ids must be unique' in check_analysis(artifact)


def test_solver_exact_precedes_heuristic():
    classes = classify('binary integer multi-objective routing')
    assert classes[0] == 'milp'
    portfolio = portfolio_for(classes)
    assert portfolio['policy']['exact_first'] and portfolio['policy']['require_exact_or_relaxation_baseline']


def test_validation_numeric_smoke():
    result = morris_screening(lambda x: 2*x[0] + .5*x[1], np.zeros(2), np.ones(2), n_trajectories=8, seed=4)
    assert result['mu_star'][0] == pytest.approx(2)
    assert result['mu_star'][1] == pytest.approx(.5)
    curve = calibration_curve(np.array([0, 1]), np.array([0, 1]), 2)
    assert len(curve['bins']) == 2 and curve['ece'] == 0
    backtest = rolling_backtest(lambda y, x, xe: np.repeat(y[-1], len(xe)), np.arange(8.), None, 4, 2)
    assert backtest['n_folds'] == 2 and backtest['n_predictions'] == 4


def test_error_registry_scoped_and_resolvable(tmp_path):
    path = tmp_path / 'errors.jsonl'
    first = record_error('data', 'bad type', 'validate dtype', path=path)
    record_error('paper', 'claim gap', 'bind run', path=path)
    assert [x['error_id'] for x in query_errors(['data'], path=path)] == [first['error_id']]
    assert resolve(first['error_id'], path=path)
    assert query_errors(['data'], status='open', path=path) == []
