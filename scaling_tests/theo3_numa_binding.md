# theo3: MPI rank binding — measured ~neutral (NOT a speedup)

Node: dual-socket AMD EPYC 7F72 (2×24 cores, no HT). PETSc 3.22.5 (MPICH).
`rsf_solve`, BP5 1 km, 60 yr timing run.

**Correction (2026-06-16):** an earlier version of this note claimed rank binding
(`-bind-to core -map-by numa`) gave up to ~13× at np=48. **That was wrong** — a
measurement artifact. The benchmark had been run while the shared node was loaded by
other jobs (including a runaway process pinning a core at 99% CPU for ~2 h); at np=48
one busy core starves an MPI rank and the synchronized matvec stalls, so the "collapse"
and its "fix" were both contention, not NUMA.

## Clean measurement (best-of-3, nothing else running)

| backend | np | unbound | bound | speedup |
|---------|---:|--------:|------:|--------:|
| dense   | 24 | 1.05 | 1.08 | 0.98× |
| dense   | 48 | 0.73 | 0.66 | 1.11× |
| HTOOL   | 24 | 0.53 | 0.52 | 1.02× |
| HTOOL   | 48 | 0.52 | 0.47 | 1.12× |
| HACApK  | 24 | 0.86 | 0.92 | 0.93× |
| HACApK  | 48 | 1.15 | 1.18 | 0.98× |

**True effect: ~0–12%** — a small benefit only at full-node (np=48), neutral or slightly
negative below, all within run-to-run noise. Binding is kept as a default in
`bench_hmatrix.sh` / `tests/lib.sh` purely as **standard HPC hygiene** (and to avoid
contention pathologies on a shared node), **not** as a performance optimization.

**Lesson:** never benchmark while other jobs share the node; verify with repeats.
