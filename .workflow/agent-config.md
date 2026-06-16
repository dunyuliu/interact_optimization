# Campaign config — interact_optimization perf/scaling (theo3, NO GPU)

Conductor: **wei-lin**. Primary optimizer: **mira-volkov** (one per task).
Branch: `autopilot/perf-2026-06-15`. Budget: 48 h from 2026-06-15 23:00.
Hourly concise briefing to the user (heartbeat owned by the main loop).

## Build
`bash build_theo3.sh`  (PETSc 3.22.5 @ /home/utig5/dmay/software, arch-linux-opt-theo;
HACApK built; hmmvp off; `-Ofast -march=native`). All run artifacts in `runs/` (git-ignored).

## Test tiers (the gate — never merge without a green tier that exercises the new path)
- **smoke** (every landing, ~1–2 min): `bash build_theo3.sh && bash tests/run_anchor.sh all`
  → inputs spec+regen, cross-backend trace, **physics: recurrence vs golden AND vs published
  236.81 yr + cumulative slip** at 2 km. Integrator/backend changes are exercised through a
  full event here.
- **fast** (every 2–3 patches or 4 h): smoke + `bash tests/run_anchor.sh perf 'dense hacapk htool' '1 2 4 8'`
  + snapshot perf CSV. 1 km physics spot-check vs published 234.29 yr (`RES=1km`).
- **full** (milestone / pre-release): fast + the scaling matrix (M-scaling-matrix) + 1 km physics.

## Success criterion (user-defined) → triggers release
**BOTH** must hold, reproducibly:
1. **Accuracy gate**: `tests/run_anchor.sh all` green (recurrence within tol vs golden *and* vs
   published; cumulative slip within tol).
2. **Performance gain**: measurable drop in the cost metric on the anchor case — primary metric
   **total matvecs** (`MatMult` count) and/or **perf-tier wallclock** — vs the pre-mission baseline,
   reproduced (not run-to-run noise).

## Release (on success only)
Run the `release` skill (semver bump + changelog/notes + commit), then **push the branch and the
version tag to `origin` (the user's fork) — fork ONLY, never upstream.** No PR/merge to the fork's
default branch without explicit user OK.

## Version scheme
Semver on this branch. If a VERSION file / git tag exists, continue from it; else baseline
`v0.1.0-opt`. **minor** bump per released perf win; **patch** for fixes/reverts.

## Subagent menu
- **mira-volkov** — numerical optimization / precision / kernel work (primary, per task)
- **iris-vermeulen** — extend the test anchor when a mission needs new coverage
- **lars-eriksson** — audit a changed kernel for math/sign/edge bugs (read-only)
- **rafael-santos / ingrid-lindqvist** — verify physics/numerics of integrator or precision changes
- **haruto-nakamura** — execute the release (notes, tag, push-to-fork)

## Discipline
Revert + log any regression (don't suppress). One subagent per file at a time. Log every
landing/revert to `runs/campaign/session-log.md`. Stop at 48 h; produce an end-of-campaign report.

## Mission queue (GPU-free; priority order)
1. **M-integrator** — minimize total matvecs via TS integrator + adapt controller + tol, recurrence
   within tol at 2 km AND 1 km. Probe: rk5dp+dsp −12 % (Δ0.033 yr), rk3bs −18 % (Δ0.042 yr).
   Pick the best safe config; make it the rsf_solve default if it passes. **(start here)**
2. **M-precision** — scope/prototype mixed/single-precision matvec (bandwidth-bound → up to ~2×;
   `makefile.mixed` exists; rtol=1e-4 floor admits single-prec matvec). Assess feasibility (single-
   prec PETSc arch and/or single-prec HACApK) before committing effort.
3. **M-backend-default** — codify per-machine backend pick (theo3: HTOOL wins np≥2 at 1 km, opposite
   of walter); consider auto-select.
4. **M-scaling-matrix** — complete theo3 scaling matrix (dense/htool/hacapk × np{1,2,4,8,16,24,48} ×
   {2 km,1 km,0.5 km}); update docs.
5. **M-microbench** — resolve compress_interaction_matrix vs rsf_solve discrepancy (matched
   compressor/tol/cores).
6. **M-longrun-crossover** — measure the ~10⁴-step HACApK vs HTOOL crossover (docs only extrapolate).
