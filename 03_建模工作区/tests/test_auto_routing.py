from pathlib import Path
import pytest
from scripts.auto_route import route_task


def manifest(*approved):
    return {'stages': [
        {'name': f'G{i} gate', 'status': 'approved' if f'G{i}' in approved else 'pending',
         'approved_by': 'human user' if f'G{i}' in approved else None,
         'approved_at': '2026-09-05T12:00:00+08:00' if f'G{i}' in approved else None}
        for i in range(1, 8)]}


@pytest.mark.parametrize(('text','skill','agents'), [
    ('请做问题拆解和假设账本', 'mm-problem-analysis', ['researcher']),
    ('检查数据质量和数据泄漏', 'mm-data-audit', ['researcher']),
    ('拟定求解器策略', 'mm-solver-strategy', ['researcher']),
    ('把已选路线做数学推导并检查单位一致性', 'mm-mathematical-derivation', ['deriver']),
    ('做模型验证与不确定性量化', 'mm-validation-uq', ['optimizer']),
    ('检查运行记录和最小复现命令', 'mm-reproducibility', ['replicator']),
    ('撰写论文摘要', 'mm-paper-writing', []),
    ('撰写 CUMCM 国赛论文摘要', 'mm-cumcm-paper-writing-review', []),
])
def test_capability_routing(text, skill, agents):
    decision = route_task(text, manifest('G1','G2','G3','G4','G5'))
    assert decision.primary_skill == skill
    assert decision.agents == agents
    assert decision.action == 'route'


def test_read_only_review_roles_are_wired():
    route = route_task('做模型验证和压力测试', manifest('G1','G2','G3','G4'))
    assert route.review_agents == ['validator', 'replicator']
    tournament = route_task('比较候选路线', manifest('G1'))
    assert tournament.review_agents == ['judge']


def test_paper_route_uses_executable_claim_registry_contract():
    decision = route_task('撰写论文摘要', manifest('G1','G2','G3','G4','G5'))
    assert any(path.endswith('claim_registry.jsonl') for path in decision.inputs + decision.outputs)


def test_route_tree_natural_language_variant():
    decision = route_task('比较两个候选建模路线并做有限预算方案树', manifest('G1'))
    assert decision.primary_skill == 'mm-route-tournament'


def test_tuning_and_validation_are_separate_routes():
    ready = manifest('G1','G2','G3','G4')
    assert route_task('做参数调优和超参数搜索', ready).primary_skill == 'mm-experiment-optimization'
    assert route_task('做敏感性分析和鲁棒性验证', ready).primary_skill == 'mm-validation-uq'


def test_derivation_does_not_swallow_neighboring_routes():
    ready = manifest('G1', 'G2')
    assert route_task('做问题拆解和量纲分析', ready).primary_skill == 'mm-problem-analysis'
    assert route_task('检查 MODEL_SPEC 的方程', ready).primary_skill == 'mm-model-spec'
    assert route_task('从假设推导控制方程', ready).primary_skill == 'mm-mathematical-derivation'


def test_human_gates_stop_and_prerequisites_block():
    assert route_task('批准基线', manifest()).action == 'stop_human_gate'
    blocked = route_task('撰写论文摘要', manifest())
    assert blocked.action == 'blocked_prerequisite' and blocked.gate == 'G5'


def test_irrelevant_and_fallback_do_not_guess():
    assert route_task('播放音乐', manifest(), project_related=False).action == 'irrelevant'
    assert route_task('做一个无法确定类别的复杂事情', manifest()).action == 'fallback_orchestrator'
