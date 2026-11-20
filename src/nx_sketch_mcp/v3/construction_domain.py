"""Evaluate explicit necessary candidate domain checks, not full topology validity."""
import math
from .regional_construction import build_candidate


def assess_candidate_domain(root, overrides=None):
    model = build_candidate(root, overrides)
    p = model['parameters']
    half = p['slot.width']/2
    R = p['stock.R0']
    radicand = p['slot.radius']**2 - (p['stock.Y0']-p['slot.axis_y'])**2
    z_side_sq = R*R-half*half
    if radicand > 0 and z_side_sq > 0:
        lower = p['slot.axis_z']-math.sqrt(radicand)
        upper = p['slot.axis_z']+math.sqrt(radicand)
        stock_top = math.sqrt(z_side_sq)
        slot_tail = -stock_top < lower < stock_top < upper
    else:
        lower = upper = stock_top = None
        slot_tail = False
    checks = [
        {'id':'slot_tail_finite_cylinder_and_two_sidewalls', 'passed':slot_tail,
         'formula':'|width/2|<R0; radius²>(Y0-axis_y)²; -zside<axis_z-sqrt(radius²-(Y0-axis_y)²)<zside<axis_z+sqrt(radius²-(Y0-axis_y)²)',
         'values_mm':{'width_half':half,'stock_radius':R,'lower_tool_z':lower,'upper_tool_z':upper,'stock_side_z':stock_top},
         'scope':'tail cross-section only; does not establish full slot exit, material or valid edits'},
        {'id':'stock_s10_radial_step','passed':p['stock.R11']>p['stock.M10'],
         'formula':'stock.R11>stock.M10','scope':'one necessary condition only'},
        {'id':'stock_s14_radial_step','passed':p['stock.R14']>p['stock.R13'],
         'formula':'stock.R14>stock.R13','scope':'one necessary condition only'},
        {'id':'stock_s19_lower_branch',
         'passed':0<p['stock.R17']-p['stock.M19']<p['stock.tube_R19'] and
                  p['stock.Ycenter19']-p['stock.tube_R19']<p['stock.Y18']<p['stock.Ycenter19']<p['stock.Y_mouth']<p['stock.Ycenter19']+p['stock.tube_R19'],
         'formula':'0<R17-M19<tube_R19 and Ycenter19-tube_R19<Y18<Ycenter19<Y_mouth<Ycenter19+tube_R19',
         'scope':'candidate branch at evaluated parameter values only'},
    ]
    return {'schema':'p3-candidate-domain-necessary-checks/0.1','checks':checks,
            'all_listed_checks_passed':all(x['passed'] for x in checks),
            'edit_domain_validity':'not_established',
            'remaining':['simple meridian and complete branch/topology preservation after edit',
                         'full slot side and center exit, source material and intersections after edit',
                         'head/stock and cutter clearances and local trims after edit',
                         'C5 six-edge, roll-axis, 22-member and source budget after edit',
                         'native solver and full geometry verification'],
            'interpretation':'these are finite binary64 candidate checks, not interval-certified manufacturing or source geometry bounds',
            'execution_approved':False}
