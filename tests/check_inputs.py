#!/usr/bin/env python3
"""
check_inputs.py -- verify the BP5 INPUT files against the SEAS BP5-QD spec
(Jiang et al. 2022; https://strike.scec.org/cvws/seas/download/SEAS_BP5.pdf),
independent of trusting make_bp5.py, plus a regeneration regression.

Two layers:
  (A) spec conformance -- parse the committed geom/rsf/ic/dc files and assert
      they satisfy the benchmark definition (geometry extent, cell count, the
      VW/VS a-distribution, uniform b, sigma, D_c bulk/nucleation, the
      nucleation patch, and the steady-state tau0 = Eq.16 closed form).
  (B) regeneration  -- re-run make_bp5.py and assert the committed files still
      match what the current generator emits (catches silent input drift).

Usage:  check_inputs.py [--repo DIR] [--ds 2.0]
"""
import argparse, os, subprocess, sys, tempfile
import numpy as np

# ---- BP5-QD spec constants (the external truth) ----
# sig in Pa for the parsing checks; the tau0 closed form is reproduced in the
# SAME mixed-unit (GPa, km/s, MPa) convention make_bp5.py uses, which matches
# the HBI radiation-damping numeric convention (see bp5/README.md Eq.16).
SPEC = dict(Lx=100.0, Ld=40.0, a0=0.004, amax=0.04, b=0.03,
            dc=0.14, dc_nuc=0.13, f0=0.6, V0=1e-6, Vpl=1e-9, sig=25.0e6,
            G=32.04e9, cs=3464.0, Vnuc=3e-2,
            G_GPa=32.04, cs_kms=3.464, sig_MPa=25.0)

def fail(msg, fails): fails.append(msg); print(f"   FAIL  {msg}")
def ok(msg):          print(f"   ok    {msg}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument('--ds', type=float, default=2.0)
    a = ap.parse_args()
    ds, bp5 = a.ds, os.path.join(a.repo, 'bp5')
    tag = f"{ds:g}km"
    fails = []
    print(f"== BP5 input verification (ds={tag}) ==")

    geom = np.loadtxt(f"{bp5}/geom_bp5_{tag}.in")           # x y z strike dip L W group
    rsf  = np.loadtxt(f"{bp5}/rsf_bp5_{tag}.dat")           # a b
    ic   = np.loadtxt(f"{bp5}/ic_bp5_{tag}.in")             # tau[Pa] v[m/s]
    dc   = np.loadtxt(f"{bp5}/dc_bp5_{tag}.in")             # D_c[m]
    n = geom.shape[0]

    # ---- (A) spec conformance ----
    nexp = int(round(SPEC['Lx']/ds)) * int(round(SPEC['Ld']/ds))
    (ok if n == nexp else lambda m: fail(m, fails))(f"cell count {n} == {nexp}")
    if not (rsf.shape[0] == ic.shape[0] == dc.shape[0] == n):
        fail("per-cell file row counts disagree", fails)

    y, z = geom[:,1], geom[:,2]                              # along-strike[m], -depth[m]
    half = geom[0,5]
    (ok if abs(half - ds*1e3/2) < 1 else lambda m: fail(m, fails))(f"half-length {half} m == {ds*1e3/2}")
    (ok if np.allclose(geom[:,3],0) and np.allclose(geom[:,4],90) else lambda m: fail(m,fails))("strike=0, dip=90 (vertical strike-slip)")
    (ok if abs(y.min()/1e3 + SPEC['Lx']/2) < ds and abs(y.max()/1e3 - SPEC['Lx']/2) < ds else lambda m: fail(m,fails))(f"strike extent ~+-{SPEC['Lx']/2} km")
    dep = -z/1e3
    (ok if dep.min() >= 0 and abs(dep.max()-SPEC['Ld']) < ds else lambda m: fail(m,fails))(f"depth extent ~0..{SPEC['Ld']} km")

    aa, bb = rsf[:,0], rsf[:,1]
    (ok if np.allclose(bb, SPEC['b']) else lambda m: fail(m,fails))(f"b uniform == {SPEC['b']}")
    (ok if abs(aa.min()-SPEC['a0'])<1e-9 and abs(aa.max()-SPEC['amax'])<1e-9 else lambda m: fail(m,fails))(f"a in [{SPEC['a0']}, {SPEC['amax']}] (VW core / VS exterior)")
    nvw = int((aa < 0.01).sum())
    (ok if nvw > 0 else lambda m: fail(m,fails))(f"VW core present: {nvw} cells with a<0.01")

    # D_c: bulk 0.14, reduced 0.13 inside the nucleation patch only
    uvals = sorted(set(np.round(dc, 6)))
    (ok if uvals == sorted({SPEC['dc'], SPEC['dc_nuc']}) else lambda m: fail(m,fails))(f"D_c values {uvals} == {sorted({SPEC['dc'],SPEC['dc_nuc']})}")
    nnuc_dc = int(np.isclose(dc, SPEC['dc_nuc']).sum())

    # nucleation patch: high initial velocity Vnuc, co-located with reduced D_c
    v = ic[:,1]
    nnuc_v = int(np.isclose(v, SPEC['Vnuc']).sum())
    (ok if nnuc_v > 0 and nnuc_v == nnuc_dc else lambda m: fail(m,fails))(f"nucleation patch: {nnuc_v} cells at v={SPEC['Vnuc']} m/s, co-located with reduced D_c ({nnuc_dc})")
    (ok if np.isclose(v[v < SPEC['Vnuc']/2], SPEC['Vpl']).all() else lambda m: fail(m,fails))(f"background v == Vpl={SPEC['Vpl']} m/s")

    # tau0 closed form (Eq.16), reproduced in make_bp5.py's mixed-unit / HBI
    # convention: eta = G[GPa]/(2 cs[km/s]); tau[Pa] = 1e6 * sig[MPa] *
    #   (a*asinh(0.5 v/V0 exp((f0 + b ln(V0/Vpl))/a)) + eta v)
    eta = SPEC['G_GPa']/(2*SPEC['cs_kms'])
    mu_ss = aa*np.arcsinh(0.5*v/SPEC['V0']*np.exp((SPEC['f0']+SPEC['b']*np.log(SPEC['V0']/SPEC['Vpl']))/aa))
    tau_exp = 1e6*SPEC['sig_MPa']*(mu_ss + eta*v)
    rel = np.max(np.abs(ic[:,0]-tau_exp)/np.maximum(np.abs(tau_exp),1e-30))
    (ok if rel < 1e-5 else lambda m: fail(m,fails))(f"tau0 matches steady-state Eq.16 (max rel {rel:.2e})")

    # ---- (B) regeneration regression ----
    print("== regeneration (generator vs committed) ==")
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run([sys.executable, f"{bp5}/make_bp5.py", str(ds)], cwd=td,
                           capture_output=True, text=True)
        if r.returncode != 0:
            fail(f"make_bp5.py failed: {r.stderr.strip()}", fails)
        else:
            for fn, ref in [(f"geom_bp5_{tag}.in", geom), (f"rsf_bp5_{tag}.dat", rsf),
                            (f"ic_bp5_{tag}.in", ic), (f"dc_bp5_{tag}.in", dc)]:
                gen = np.loadtxt(os.path.join(td, fn))
                if gen.shape == ref.shape and np.allclose(gen, ref, rtol=1e-8, atol=0):
                    ok(f"{fn} reproduces committed")
                else:
                    fail(f"{fn} differs from committed (input drift)", fails)

    print("== RESULT:", "PASS ==" if not fails else f"FAIL ({len(fails)}) ==")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
