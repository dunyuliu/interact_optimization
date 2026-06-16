# `tests/` — the regression / correctness / performance anchor

A performance optimization is only safe if it provably **does not change the
physics**. This directory is that proof: every change to a backend, the
integrator, the kernels, or the build must still reproduce the SEAS BP5-QD
benchmark to tolerance, or `run_anchor.sh` fails loudly.

The anchor case is **BP5-QD at 2 km / 1000 cells** — small enough to run in
seconds, but it still reproduces the real physics (first spontaneous recurrence
at **236.81 yr**, matching HBI and the published BEM cluster). The golden was
blessed from a `-use_hmatrix 0` (dense) run, which is the exact ground truth.

## Run it

```bash
bash build_theo3.sh                 # build rsf_solve first (see ../build_theo3.sh)
bash tests/run_anchor.sh all        # inputs + smoke + physics   (~30 s)
bash tests/run_anchor.sh inputs     # BP5 inputs vs spec + regeneration
bash tests/run_anchor.sh smoke      # interseismic trace, all backends agree (~5 s)
bash tests/run_anchor.sh physics    # full cycle: recurrence + slip vs golden & published
bash tests/run_anchor.sh perf 'dense hacapk htool' '1 2 4'   # timings vs baseline
```

Exit code is nonzero on any failure. All run artifacts land in `../runs/anchor/`
(git-ignored). Nothing here writes into the source tree.

## What each tier anchors

| tier | what it verifies | gate |
|------|------------------|------|
| **inputs** | BP5 input files satisfy the published spec (cell count, geometry extent, VW/VS `a`-distribution, uniform `b`, σ, `D_c` bulk/nucleation, nucleation patch, and the τ₀ = steady-state Eq. 16 closed form) **and** still match `make_bp5.py` output | spec + regeneration |
| **smoke** | dense ≡ HACApK ≡ HTOOL on the **interseismic** `log10\|v\|` trace over [0, 50 yr] | trace RMS / max (tight) |
| **physics** | first spontaneous **recurrence** (vs the self-golden *and* vs the published 236.81 yr) + **cumulative slip** at 246 yr | recurrence + slip |
| **perf** | assembly / matvec / total wallclock per (backend, np), recorded to CSV | informational, vs baseline |

## Two layers of correctness

1. **Regression** (same backend as golden → near bit-identical): catches any
   unintended change. `dense` reproduces the golden to `0.000e+00`.
2. **External validation** (vs HBI / Jiang et al. 2022): the recurrence is also
   checked against the **published** 236.81 yr, independent of the self-golden —
   so a corrupted re-bless cannot silently hide a physics regression.

## Why the coseismic trace is *not* a hard gate

Across an event the `max|v|` trace jumps ~9 orders of magnitude in well under a
year. A sub-0.001-yr difference in event timing between two backends then makes a
*pointwise* trace difference meaningless (one run is mid-rupture, the other isn't,
at the same sample time) — the artifact `bp5/README.md` documents. So the event
is anchored by its **onset time** and by **cumulative slip** (both robust); the
pointwise trace is gated only in the quiescent interseismic regime (smoke), and
shown as info during physics.

## Re-blessing the golden

Only after a **deliberate, verified** physics change:

```bash
bash tests/run_anchor.sh bless      # regenerate golden/ from the current dense build
```

The external-reference check (236.81 yr) still guards against blessing a wrong
golden. Tolerances and the reference value live in `run_anchor.sh` / `check_anchor.py`.
