#!/usr/bin/env python3
"""
check_anchor.py -- compare an rsf_solve run against the blessed golden, within
tolerance, and exit nonzero on failure.

It anchors three deterministic, physically-meaningful quantities:

  1. First spontaneous event onset time [yr]   (the BP5 recurrence; sharp scalar)
  2. log10(max|v|) trace over a time window     (RMS + max deviation)
  3. Final-state mean slip [m] and end time     (long-run integral check)

Two tolerance regimes:
  --mode regression : candidate uses the SAME backend as the golden (dense).
                      Expect (near) bit-identical reproduction -> very tight.
  --mode equiv      : candidate uses a different backend (HACApK/HTOOL/...).
                      Expect physical agreement at the ODE-tolerance floor;
                      the docs report <0.01 yr recurrence and <=0.005 log-unit
                      trace agreement -- we allow a safe margin above that.

Usage:
  check_anchor.py --run DIR --golden DIR [--window 50|all]
                  [--mode regression|equiv] [--no-event]
"""
import argparse, sys
import numpy as np

def load_monitor(path):
    # cols: step time_s time_yr dt log10|v| mean_slip mean_mu max_sig min_sig
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            p = line.split()
            if len(p) < 6:
                continue
            rows.append((float(p[2]), float(p[4]), float(p[5])))  # t_yr, log10v, mean_slip
    a = np.array(rows)
    return a[:,0], a[:,1], a[:,2]   # t, logv, slip

def first_spontaneous_onset(events_path):
    # events: time_s time_yr flag(1 onset / -1 arrest) ...
    with open(events_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            p = line.split()
            t_yr, flag = float(p[1]), int(float(p[2]))
            if flag == 1 and t_yr > 1.0:    # skip the t~=0 nucleation event
                return t_yr
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--golden', required=True)
    ap.add_argument('--window', default='all', help="'all' or an upper time in yr (smoke)")
    ap.add_argument('--mode', default='equiv', choices=['regression','equiv'])
    ap.add_argument('--no-event', action='store_true',
                    help='skip the recurrence check (window too short to reach it)')
    ap.add_argument('--ref-recurrence', type=float, default=None,
                    help='external published/HBI recurrence [yr] to validate against '
                         '(independent of the self-golden)')
    ap.add_argument('--ref-tol', type=float, default=0.1,
                    help='tolerance [yr] for the external-reference recurrence check')
    ap.add_argument('--trace', choices=['gate','info'], default='gate',
                    help="gate: trace deviation is pass/fail (smoke, interseismic-only). "
                         "info: print but don't fail (physics -- the event ramp makes a "
                         "pointwise trace diff timing-sensitive; recurrence+slip gate instead)")
    ap.add_argument('--seismic-cut', type=float, default=-4.0,
                    help='exclude trace samples where golden log10|v| exceeds this '
                         '(coseismic spike: a sub-0.001 yr event-timing shift makes a '
                         'pointwise trace diff meaningless; the event is anchored by '
                         'onset time + final slip instead)')
    a = ap.parse_args()

    if a.mode == 'regression':
        tol_event, tol_rms, tol_max, tol_slip = 1e-3, 1e-6, 1e-5, 1e-6   # ~bit-identical
    else:
        tol_event, tol_rms, tol_max, tol_slip = 0.05, 0.02, 0.08, 0.02   # physical agreement

    gt, glv, gsl = load_monitor(f"{a.golden}/bp5_2km_dense.monitor"
                                if a.golden.endswith('golden') else f"{a.golden}/rsf_monitor.dat")
    rt, rlv, rsl = load_monitor(f"{a.run}/rsf_monitor.dat")

    wins = (gt.max() if a.window == 'all' else float(a.window))
    # interseismic mask: drop the coseismic spike (see --seismic-cut)
    m = (gt <= wins) & (glv <= a.seismic_cut)
    ncos = int(((gt <= wins) & (glv > a.seismic_cut)).sum())
    # interpolate candidate trace onto golden's (windowed, interseismic) time grid
    rlv_i = np.interp(gt[m], rt, rlv)
    d = rlv_i - glv[m]
    rms = float(np.sqrt(np.mean(d**2)))
    mx  = float(np.max(np.abs(d)))

    fails = []
    print(f"  trace window  : [0, {wins:.1f}] yr, {m.sum()} interseismic samples"
          + (f" ({ncos} coseismic excluded)" if ncos else ""))
    tag = '' if a.trace == 'gate' else '  [info]'
    print(f"  trace RMS     : {rms:.3e} log-units   (tol {tol_rms:.0e}){tag}")
    print(f"  trace max|Δ|  : {mx:.3e} log-units   (tol {tol_max:.0e}){tag}")
    if a.trace == 'gate':
        if rms > tol_rms: fails.append(f"trace RMS {rms:.3e} > {tol_rms:.0e}")
        if mx  > tol_max: fails.append(f"trace max {mx:.3e} > {tol_max:.0e}")

    # final-state mean slip (compare at the candidate's last time within window)
    if a.window == 'all':
        gslip_end, rslip_end = gsl[-1], rsl[-1]
        rel = abs(rslip_end - gslip_end) / max(abs(gslip_end), 1e-30)
        print(f"  final slip    : run {rslip_end:.6f} vs golden {gslip_end:.6f} m  (rel {rel:.2e}, tol {tol_slip:.0e})")
        if rel > tol_slip: fails.append(f"final slip rel {rel:.2e} > {tol_slip:.0e}")

    # recurrence (first spontaneous onset)
    if not a.no_event:
        ge = first_spontaneous_onset(f"{a.golden}/bp5_2km_dense.events"
                                     if a.golden.endswith('golden') else f"{a.golden}/rsf_events.dat")
        re = first_spontaneous_onset(f"{a.run}/rsf_events.dat")
        if ge is None or re is None:
            fails.append(f"recurrence not found (golden={ge}, run={re})")
            print(f"  recurrence    : MISSING (golden={ge}, run={re})")
        else:
            de = abs(re - ge)
            print(f"  recurrence    : run {re:.4f} vs golden {ge:.4f} yr  (Δ {de:.4f}, tol {tol_event:.0e})")
            if de > tol_event: fails.append(f"recurrence Δ {de:.4f} yr > {tol_event:.0e}")
            # external validation: vs the published / HBI reference, not the self-golden
            if a.ref_recurrence is not None:
                dref = abs(re - a.ref_recurrence)
                print(f"  vs published  : run {re:.4f} vs ref {a.ref_recurrence:.2f} yr  (Δ {dref:.4f}, tol {a.ref_tol:.2f})")
                if dref > a.ref_tol: fails.append(f"recurrence vs published Δ {dref:.4f} yr > {a.ref_tol:.2f}")

    if fails:
        print("  RESULT        : FAIL -- " + "; ".join(fails))
        sys.exit(1)
    print("  RESULT        : PASS")
    sys.exit(0)

if __name__ == '__main__':
    main()
