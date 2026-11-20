"""Evidence-scoped, advisory comparisons of editable feature history options.

This module neither changes a plan nor authorizes native execution. Exact
expression identities are required: equality of nominal values is insufficient.
"""
from collections import Counter
import json
from pathlib import Path
from .project_root import project_root

_REVIEWED_SOURCE_MAP = 'workspace/v3/p3/P3-SWEPT-ANALYSIS-01/source-map.json'

# One shared, advisory policy for MCP initialization and every guidance result.
SKETCH_PREFERENCE = (
    "Before modeling, when supported by the target NX version and a native "
    "parametric sketch can express the geometry and intended edit relationships, "
    "prefer it. Create the lines, arcs and splines of the same planar profile "
    "directly as geometry in one native sketch, drive it with dimensional and "
    "geometric constraints, and reference that sketch as the section for "
    "extrusion or revolve. Avoid creating each profile curve as a separate "
    "curve feature. This can reduce features in the history tree and make edits "
    "more convenient. Preserve independent profiles when their edits should "
    "remain independent."
)


NAMING_PREFERENCE = (
    "Name sketches and features for their modeling purpose or part region, "
    "for example 'Shaft Profile' and 'Bearing Seat Cut'. Use display names "
    "where the available interface supports them. Keep logical IDs and session "
    "bindings for object identification."
)


def design_guidance_base():
    """Create a fresh guidance envelope, even when no candidate is available."""
    return {'schema': 'v3-design-guidance/1', 'status': 'advisory_only',
            'execution_approved': False,
            'preferences': [{'id': 'prefer_native_parametric_sketch',
                             'recommendation': SKETCH_PREFERENCE},
                            {'id': 'name_sketches_and_features_by_purpose',
                             'recommendation': NAMING_PREFERENCE}]}


def reviewed_layout_evidence():
    """Read the fixed reviewed P3 bridge, never a path supplied by a plan."""
    path = project_root() / _REVIEWED_SOURCE_MAP
    try:
        with path.open(encoding='utf-8-sig') as stream:
            return {'path': _REVIEWED_SOURCE_MAP, 'data': json.load(stream)}
    except (OSError, ValueError):
        return None


def _driven_edges(edges, expressions):
    if not isinstance(edges, list) or not edges:
        return False
    for edge in edges:
        if not isinstance(edge, dict):
            return False
        kind = edge.get('kind')
        keys = {'line': {'kind', 'start', 'end', 'point_expressions'},
                'arc': {'kind', 'start', 'mid', 'end', 'point_expressions'},
                'spline': {'kind', 'method', 'order', 'knots', 'poles', 'pole_expressions'}}
        if kind not in keys or set(edge) != keys[kind]:
            return False
        field = 'pole_expressions' if kind == 'spline' else 'point_expressions'
        expected = {'line': 2, 'arc': 3}.get(kind)
        rows = edge.get(field)
        if kind not in ('line', 'arc', 'spline') or not isinstance(rows, list) or not rows:
            return False
        if expected is not None and len(rows) != expected:
            return False
        if kind == 'spline' and len(rows) != len(edge.get('poles', [])):
            return False
        if any(not isinstance(row, list) or len(row) != 3 or
               any(not isinstance(name, str) or expressions.get(name) != 1 for name in row)
               for row in rows):
            return False
    return True


def _layout_members(plan, decision, binding, faces, layout_evidence):
    """Return current members only when the observation is bound to this plan."""
    snapshot = plan.get('p1_snapshot_id')
    construction = plan.get('construction', {})
    members = construction.get('members', []) if isinstance(construction, dict) else []
    if not isinstance(snapshot, str) or not snapshot or not isinstance(members, list) or len(members) != len(faces):
        return None
    if any(not isinstance(m, dict) or type(m.get('member_index')) is not int
           or not isinstance(m.get('p1_cylinder_face'), str) or not m['p1_cylinder_face'] for m in members):
        return None
    current = {m['member_index']: m['p1_cylinder_face'] for m in members}
    if len(current) != len(members) or len(set(current.values())) != len(members):
        return None
    decisions = plan.get('user_decisions', [])
    if not isinstance(decisions, list):
        return None
    # A known cross-snapshot bridge must not be bypassed by relabelling its
    # observation as the current snapshot, even if the face labels coincide.
    has_bridge = any(isinstance(item, dict) and isinstance(item.get('record'), dict)
                     and isinstance(item['record'].get('source_binding'), dict)
                     and item['record']['source_binding'].get('relation_decision_path') == decision.get('path')
                     for item in decisions)
    evidence_data = layout_evidence.get('data') if isinstance(layout_evidence, dict) else None
    known_decision = evidence_data.get('decision') if isinstance(evidence_data, dict) else None
    if isinstance(known_decision, dict) and known_decision.get('path') == decision.get('path'):
        has_bridge = True
    if binding['snapshot_id'] == snapshot and not has_bridge:
        return list(current.values()) if set(current.values()) == set(faces) else None
    for item in decisions:
        if not isinstance(item, dict) or not isinstance(item.get('record'), dict):
            continue
        record = item['record']; scope = record.get('scope'); source = record.get('source_binding')
        if (record.get('authority') != 'explicit user reply in this conversation'
                or not isinstance(scope, dict) or scope.get('position_by_confirmed_equal_angular_relation') is not True
                or scope.get('fixed_count') != len(faces) or not isinstance(source, dict)
                or source.get('p1_snapshot_id') != snapshot
                or source.get('relation_decision_path') != decision.get('path')):
            continue
        mapped = source.get('members')
        evidence = layout_evidence.get('data') if isinstance(layout_evidence, dict) else None
        source_decision = evidence.get('decision') if isinstance(evidence, dict) else None
        if (not isinstance(evidence, dict) or evidence.get('schema') != 'p3-swept-source-map/0.1'
                or evidence.get('p1_snapshot_id') != snapshot or evidence.get('members') != mapped
                or layout_evidence.get('path') != source.get('source_map_path')
                or not isinstance(source_decision, dict)
                or source_decision.get('path') != decision.get('path')
                or source_decision.get('decision_id') != decision['record'].get('decision_id')
                or source_decision.get('decision_snapshot_id') != binding['snapshot_id']
                or source_decision.get('reference_analysis_path') != binding['analysis_path']
                or source_decision.get('scope') != decision['record'].get('scope')):
            continue
        if (not isinstance(mapped, list) or len(mapped) != len(faces)
                or any(not isinstance(m, dict) or type(m.get('member_index')) is not int
                       or not isinstance(m.get('decision_snapshot_face_id'), str)
                       or not isinstance(m.get('p1_cylinder_face_id'), str) for m in mapped)):
            continue
        by_index = {m['member_index']: m['p1_cylinder_face_id'] for m in mapped}
        observed = [m['decision_snapshot_face_id'] for m in mapped]
        if len(by_index) == len(mapped) and by_index == current and len(set(observed)) == len(faces) and set(observed) == set(faces):
            return [current[m['member_index']] for m in members]
    return None


def build_design_guidance(plan, groups, *, layout_evidence=None):
    """Compare the actual lowered profile uses and confirmed layout decisions.

    Counts describe the candidate lowering, not measured NX history or proven
    savings. Only exact frame, edge and named driver equality qualifies.
    """
    steps = [step for group in groups for step in group]
    expressions = Counter(s.get('name') for s in steps if s.get('kind') == 'expression')
    profiles = [s for s in steps if s.get('kind') in ('extrude', 'revolve')]
    construction = plan.get('construction', {})
    definitions = construction.get('profiles', {})
    nodes = construction.get('nodes', [])
    identity = {n['id']: n['profile'] for n in nodes if isinstance(n, dict)
                and isinstance(n.get('id'), str) and isinstance(n.get('profile'), str)
                and n['profile'] in definitions} if isinstance(nodes, list) and isinstance(definitions, dict) else {}
    classes = []
    for step in profiles:
        if (not isinstance(step.get('id'), str) or step['id'] not in identity or not isinstance(step.get('frame'), dict)
                or not _driven_edges(step.get('edges'), expressions)):
            continue
        for group in classes:
            if (identity[step['id']] == identity[group[0]['id']] and
                    step['frame'] == group[0]['frame'] and step['edges'] == group[0]['edges']):
                group.append(step)
                break
        else:
            classes.append([step])
    actions = []
    for group in classes:
        if len(group) < 2:
            continue
        consumers = [s['id'] for s in group]
        duplicate_profiles = len(group) - 1
        actions.append({
            'action': 'review_shared_profile', 'applicable_to': consumers,
            'basis': ['Same source profile identity (' + identity[group[0]['id']] + '), identical ordered profile definitions, coordinate frame and named point drivers in the lowered steps.',
                      'Each listed operation currently creates its own profile curves.'],
            'impact': 'Editing a shared profile would affect every listed consumer; retain separate features if independent edits are required.',
            'estimated_benefit': {'duplicate_profile_instances': duplicate_profiles,
                                  'duplicate_curve_producing_features': duplicate_profiles * len(group[0]['edges']),
                                  'definition': 'For the UG11 driven-profile route, one curve-producing feature per edge per consumer; excludes operations, points, expressions and section objects. Estimate assumes one shared curve set is supported.'},
            'confirm_and_verify': ['Confirm shared design intent for all consumers and their edit propagation.',
                                   'Verify target-version support for reusing the curves, operation behavior, ordering, edits and geometry before changing the history.'],
        })
    # Similar nominal geometry is not evidence of common design identity.
    eligible = [g[0] for g in classes]
    for index, left in enumerate(eligible):
        for right in eligible[index + 1:]:
            if left['frame'] != right['frame']:
                continue
            def geometry(step):
                return [{k: v for k, v in edge.items() if k not in ('point_expressions', 'pole_expressions')}
                        for edge in step['edges']]
            if geometry(left) != geometry(right):
                continue
            actions.append({'action': 'keep_independent', 'applicable_to': [left['id'], right['id']],
                            'basis': ['Nominal profile geometry and frame match, but source profile identity or named drivers differ.'],
                            'impact': 'Separate construction preserves independent edits; equal initial values do not imply a shared design.',
                            'estimated_benefit': {'status': 'not_estimated', 'definition': 'No merging benefit is claimed.'},
                            'confirm_and_verify': ['If linkage is desired, confirm the design relationship and verify edit propagation before changing it.']})
    decisions = plan.get('user_decisions', [])
    for item in decisions if isinstance(decisions, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get('record'), dict):
            continue
        record = item['record']; scope = record.get('scope'); binding = record.get('observation_binding')
        if (not isinstance(scope, dict) or scope.get('equal_angular_spacing') is not True
                or not isinstance(scope.get('fixed_count'), int) or isinstance(scope.get('fixed_count'), bool)
                or scope['fixed_count'] < 2 or not isinstance(binding, dict)
                or record.get('authority') != 'explicit user reply in this conversation'
                or not isinstance(item.get('path'), str) or not item['path'].strip()):
            continue
        faces = binding.get('source_face_ids'); count = scope['fixed_count']
        snapshot = binding.get('snapshot_id')
        if (not isinstance(faces, list) or len(faces) != count or any(not isinstance(f, str) or not f for f in faces)
                or len(set(faces)) != count or not isinstance(snapshot, str) or not snapshot.strip()
                or not isinstance(binding.get('analysis_path'), str) or not binding['analysis_path'].strip()):
            continue
        current_members = _layout_members(plan, item, binding, faces, layout_evidence)
        if current_members is None:
            continue
        actions.append({
            'action': 'review_circular_pattern', 'applicable_to': current_members,
            'basis': ['Explicit decision confirms equal angular spacing in observation snapshot ' + snapshot + '; the applicable members are mapped to the current plan.',
                      'Analysis: ' + binding['analysis_path'],
                      'Decision: ' + item['path'], 'Current member identities are scoped to P1 snapshot ' + plan['p1_snapshot_id'] + '.'],
            'impact': 'A pattern could couple instances and shorten history; independent instance edits and individual trims may be lost.',
            'estimated_benefit': {'status': 'unknown', 'definition': 'No feature reduction is estimated from axis layout alone.'},
            'confirm_and_verify': ['Confirm complete feature geometry, cut depth, target body, trim, and independent driver intent for every instance.',
                                   'Prove complex pattern capability and edit behavior in the target NX version; verify Boolean order, geometry, regeneration and save/reopen before adoption.'],
        })
    return {**design_guidance_base(), 'actions': actions,
            'limitations': ['Equal nominal values do not establish a shared driver or design identity.',
                            'No candidate is an approved or proven optimization; missing evidence leaves independent construction unchanged.',
                            'Confirmed axis layout alone does not establish interchangeable complete features or native pattern capability.']}
