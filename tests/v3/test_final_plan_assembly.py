"""P3 final assembly checks against current accepted evidence; no NX."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'workspace/v3/p3/P3-FINAL-PLAN-01/build_plan.py'
spec = importlib.util.spec_from_file_location('p3_final_plan', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_real_source_partition_constructive_graph_and_budget_state():
    report = module.build(ROOT)
    assert report['coverage']['source_faces'] == report['coverage']['unique_source_faces'] == 235
    assert sum(len(r['faces']) for r in report['source_responsibility']) == 235
    bindings = report['face_construction_bindings']
    assert len(bindings) == len({r['source_face'] for r in bindings}) == 235
    assert all(r['construction_nodes'] and r['finite_domain'] and r['material_role'] and r['bound_record'] is not None for r in bindings)
    assert len(report['user_decisions']) == 10
    assert next(i for i in report['shared_interfaces'] if i['face'] == 'F0196')['owning_region'] == 'stock'
    nodes = {node['id']:node for node in report['construction']['nodes']}
    assert nodes['head.result']['target'] == 'member_21_result'
    params = report['parameters']['regional'] + report['parameters']['c5']
    assert sum(p['id'] == 'shaft_outer_diameter_mm' for p in params) == 1
    assert sum(p['id'] == 'stock.Y_mouth' for p in params) == 1
    assert all(p.get('unit') for p in params)
    assert all(p['classification'] in {'fixed','independent','derived'} for p in params)
    assert all(p.get('consumers') or p.get('role', '').startswith('reference_only') for p in params)
    preview = report['construction']['implementation_route']['solid_enclosure']['default_binary64_outward_preview']
    vertices = report['construction']['profiles']['stock_profile']['vertices']
    assert all(preview['y_lower_mm'] <= v['y_mm'] <= preview['y_upper_mm'] and v['radius_mm'] <= preview['radial_upper_mm'] for v in vertices)
    bound = report['combined_source_to_mathematical_boundary']
    expected_ready = all(report['readiness_checks'].values())
    assert report['p3_ready'] == expected_ready
    assert not report['execution_approved']


def test_duplicate_source_responsibility_cannot_count_as_coverage(monkeypatch):
    original = module.read
    def edited(root, path):
        doc = original(root, path)
        if str(path).replace('\\', '/').endswith('P3-DAG-02/design-dag.json'):
            doc = deepcopy(doc)
            doc['regions'][0]['responsible_faces'][0] = doc['regions'][1]['responsible_faces'][0]
        return doc
    monkeypatch.setattr(module, 'read', edited)
    with pytest.raises(ValueError, match='disjoint complete partition'):
        module.build(ROOT)


def test_shoulder_to_flank_interface_must_match_its_member(monkeypatch):
    original = module.read
    def edited(root, path):
        doc = original(root, path)
        if str(path).replace('\\', '/').endswith('P3-SHOULDER-STOCK-05/regions-interface-accepted.json'):
            doc = deepcopy(doc)
            doc['members'][0]['shoulders'][0]['source_flank_face'] = 'F9999'
        return doc
    monkeypatch.setattr(module, 'read', edited)
    with pytest.raises(ValueError, match='interfaces do not match'):
        module.build(ROOT)
