# Changelog — interact_optimization (perf/scaling campaign)

Performance/scaling work on `rsf_solve` (BP5-QD), gated by the `tests/` anchor.
Branch work on a fork; pushes to this fork only.

## v0.2.0-opt — 2026-06-16 (theo3 characterization)

**No significant speedup to the default was found** — this release is characterization
plus build/test infrastructure, honestly labeled. (An earlier draft of this release
claimed a ~13× win from MPI rank binding; that was a **measurement artifact** from a
contended node and has been **corrected** — see below.)

- **Backend ranking on theo3 flips vs walter:** with PETSc 3.22.5 + `sympartialACA`,
  **HTOOL is the fastest backend at every size/np** (0.5 km, clean: 7.1 s @ np=24, 6.5 s @
  np=48 vs HACApK 9.2/11.5, dense 63/59), and HTOOL **assembly is cheap** here (~18.7 s @
  0.5 km np=1) — not the ~38 min seen on walter. Practical recommendation on theo3:
  `-use_hmatrix 1` (HTOOL), np≈24–48, vs the HACApK default. This is a *usage* choice, not
  a code change. Tables + raw 1 km CSV: `scaling_tests/theo3_scaling_matrix.md`.
- **MPI rank binding defaulted** in `bench_hmatrix.sh`/`tests/lib.sh` as standard hygiene.
  Measured effect on theo3 is **~neutral** (0–12% at np=48, within noise) —
  *not* a speedup. See `scaling_tests/theo3_numa_binding.md`.
- **Resolved 2 open questions** for theo3: no HACApK↔HTOOL long-run crossover (HTOOL wins
  both assembly and matvec); the microbench-vs-rsf_solve discrepancy is consistent here.
- **Accuracy:** all of the above is bit-identical to the dense reference (anchor green).

## v0.1.0-opt — 2026-06-15
- Campaign baseline: reproducible theo3 build (`build_theo3.sh`) and the BP5-QD
  regression/correctness/perf anchor (`tests/`), golden blessed from the dense reference
  (recurrence 236.81 yr, matches HBI/published).

## Investigated / deferred (no code change)
- **Integrator** rk3bs+dsp cuts matvec **count** −30 % (2 km) / −40 % (1 km) within the
  0.1 yr published tolerance (matvec counts are deterministic, not contaminated), but trades
  the 0.003→0.02–0.04 yr recurrence match. **User declined** as default; available via
  `-ts_rk_type 3bs -ts_adapt_type dsp`. Patch: `runs/campaign/M-integrator-rsf_solve.patch`.
- **Mixed/single precision:** infeasible without a single-precision PETSc build or a
  multi-day HACApK port (`scaling_tests/precision_feasibility.md`).
- **BLAS dgemv kernel rewrite:** the HACApK leaf-block matvec is hand-rolled scalar loops
  (= dgemv). Rewriting them with BLAS preserved accuracy (~1e-13 parity, identical recurrence)
  but gave **0% speedup** — verified by clean A/B (best-of-3, both kernels rebuilt): 1 km
  2.31→2.31 ms, 2 km 0.153→0.153 ms. The matvec is **memory-bandwidth-bound**, so vectorizing
  the arithmetic moves the same bytes and buys nothing; small leaf blocks also negate dgemv's
  SIMD edge. Not landed (no benefit, and not bit-identical). This is the third independently
  **disproven** speedup (cf. the binding artifact), confirming bandwidth — not compute or code
  style — is the bottleneck.
