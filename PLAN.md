# interact_optimization — performance plan & status

_Last updated 2026-06-16. Machine: theo3 (2×24-core AMD EPYC 7F72, **no GPU**)._

## TL;DR
`rsf_solve`'s cost is dominated by the elastic-operator **matvec**, applied ~6 × Nsteps
(~10⁴–10⁵×) per run. On theo3 that matvec is **memory-bandwidth-bound**. Consequence:
no accuracy-preserving *code* rewrite speeds it up — the only levers are fewer bytes
(precision), fewer matvecs (integrator), or more bandwidth (GPU / multi-node).

## Recommended run recipe (theo3) — the real, available speedup
```
mpirun -bind-to core -map-by numa -np 24 bin/rsf_solve -use_hmatrix 1 -mat_htool_epsilon 1e-4 ...
```
- **`-use_hmatrix 1` (HTOOL)** beats the dense default and HACApK at every size here
  (0.5 km/np=24: 7.1 s vs dense 63 s ≈ **9×**; vs serial dense ~100×). Cheap assembly (~18.7 s).
- **np≈24** is the sweet spot (np=48 gains little — bandwidth saturates two sockets).
- Backend ranking is **hardware/build-dependent**: HACApK won on "walter"; HTOOL wins here.
  Always benchmark on the target build (`bp5/bench_hmatrix.sh`).

## How to build & verify (theo3)
- Build: `bash build_theo3.sh` (Dave May PETSc 3.22.5 + htool/h2opus; bundled HACApK; hmmvp off).
- Gate any change: `bash tests/run_anchor.sh all` — BP5-QD regression (inputs vs spec, cross-backend
  trace, recurrence vs golden AND published 236.81 yr, cumulative slip; dense is bit-identical).
  **Every perf claim must pass this anchor and be confirmed by a best-of-3 A/B (candidate vs
  baseline rebuilt under identical, idle conditions) before it counts.**

## NEXT PHASE → GPU machine (active direction)
The bottleneck is bandwidth, and a GPU's HBM (~1–3 TB/s) is ~5–15× theo3's DRAM (~0.2–0.4 TB/s) —
so the GPU is the *real* exit, not a marginal lever. `rsf_solve` already links the GPU-capable
**h2opus** backend (`-use_hmatrix 2`); it is untested only because theo3 has no GPU.

Bring-up checklist on the GPU box:
1. **PETSc with CUDA + h2opus on GPU** — configure `--with-cuda --download-h2opus` (h2opus needs
   CUDA + KBLAS/MAGMA). Make a `build_<gpu>.sh` analog of `build_theo3.sh` (new PETSC_ARCH).
2. **Build rsf_solve** against it; the bundled HACApK still builds for CPU comparison.
3. **Gate with the existing anchor — it is machine-independent.** The BP5 golden (recurrence
   236.81 yr) is *physics*, not hardware, so `tests/run_anchor.sh all` validates the GPU build
   for free. The dense-CPU regression stays bit-identical; h2opus is checked in `equiv` mode
   (recurrence within tol). If h2opus drifts, that's a real GPU-kernel bug, not noise.
4. **Benchmark** `bp5/bench_hmatrix.sh` with `-use_hmatrix 2` (h2opus/GPU) vs dense-on-GPU
   (`-mat_type aijcusparse`/`densecuda`) vs the CPU backends, at 1 km / 0.5 km and finer.
5. **Single precision is natural on GPU** (`--with-precision=single` or fp32 h2opus) — combines the
   precision lever (½ bytes) with HBM bandwidth; expect the largest gains here. Anchor-gate it.

## Other levers (CPU-side, lower priority now)
- **Single-precision HACApK (~2×, CPU)** — only worthwhile if staying CPU; multi-day Fortran port
  (`real*8`/`MPI_DOUBLE_PRECISION` across ~5 files) + parity re-validation. GPU fp32 supersedes it.
- **Multi-node MPI** — more aggregate bandwidth; HACApK is built for distributed memory. Needs a cluster.
- **Integrator `rk3bs+dsp` (−30/−40% matvec count)** — verified, within published tolerance, but
  trades the 0.003→0.04 yr recurrence match. **Declined as default**; opt-in via
  `-ts_rk_type 3bs -ts_adapt_type dsp`. Orthogonal to backend — stacks with any GPU win.

## Tried & DISPROVEN (do not re-chase — all verified no-op)
- **NUMA rank binding "~13.6×"** → **1.0×** (a contended-node measurement artifact). Binding kept
  on only as hygiene.
- **Bit-identical glue refactor** → **~1.7%** ceiling (kernel is 57% & library-bound; glue ~irreducible).
- **BLAS `dgemv` kernel rewrite "~18×"** → **1.0×** (resolution conflation; matvec is bandwidth-bound,
  so vectorizing the arithmetic moves the same bytes). Reverted.

## Artifacts
`build_theo3.sh`, `tests/`, `CHANGELOG.md`, `scaling_tests/theo3_scaling_matrix.md`,
`scaling_tests/theo3_numa_binding.md`, `scaling_tests/precision_feasibility.md`,
`runs/campaign/FINAL_REPORT.md` (full campaign record). Branch `autopilot/perf-2026-06-15`,
tags `v0.1.0-opt` (baseline) / `v0.2.0-opt` (honest characterization).
