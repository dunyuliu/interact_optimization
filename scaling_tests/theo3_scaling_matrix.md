# theo3 scaling matrix — and why it flips the walter conclusion

Node: dual-socket AMD EPYC 7F72 (2×24 cores, no HT). PETSc 3.22.5 (MPICH, Dave May build,
HTOOL compressor `sympartialACA`). `rsf_solve`, BP5 short 60 yr timing run, **NUMA rank
binding on** (`-bind-to core -map-by numa`; mandatory — see `theo3_numa_binding.md`).
Raw data: `bench_hmatrix_{2km,1km,0.5km}.theo3.csv`. One run/point — trends, not 3 sig figs.

## Total wallclock (s)

**1 km / 4000 cells** (pinned)
| np | dense | HTOOL | HACApK | fastest |
|---:|---:|---:|---:|:--|
| 1 | 28.0 | 10.2 | 10.2 | ~tie |
| 2 | 13.8 | 3.53 | 4.56 | HTOOL |
| 4 | 8.26 | 1.96 | 2.58 | HTOOL |
| 8 | 6.02 | 0.94 | 1.27 | HTOOL |
| 16 | 2.08 | 0.61 | 0.90 | HTOOL |
| 24 | 1.06 | **0.53** | 0.92 | HTOOL |
| 48 | 0.72 | 0.59 | 1.32 | HTOOL@24 |

**0.5 km / 16000 cells**
| np | dense | HTOOL | HACApK | fastest |
|---:|---:|---:|---:|:--|
| 1 | 701.7 | **97.8** | 115.6 | HTOOL |
| 4 | 214.3 | **26.6** | 32.1 | HTOOL |
| 8 | 166.4 | **16.5** | 18.7 | HTOOL |
| 16 | 89.1 | **10.2** | 11.1 | HTOOL |
| 24 | 63.1 | **7.10** | 9.17 | HTOOL |
| 48 | 58.7† | **6.50** | 11.5 | HTOOL |

(np≤24 verified clean; np=48 re-measured clean best-of-2 after a contaminated first
pass — HTOOL **improves** to 6.50 s at np=48, HACApK regresses mildly to 11.5 s.
†dense np=48 not clean-re-measured; treat as indicative.)

## Findings — opposite of the walter ranking in `rsf_solve.md`

1. **HTOOL is the fastest backend on theo3 at every size and rank count** (HACApK a close
   second). On walter HACApK won everywhere; here it does not. Backend choice is
   hardware/build-dependent — confirmed, not assumed.
2. **HTOOL assembly is cheap here**, not the bottleneck the walter run reported: 0.5 km
   single-core HTOOL assembly is **18.7 s**, versus the ~2299 s (~38 min) measured on walter.
   The `sympartialACA` default + this PETSc/Htool build removes the SVD-assembly trap
   entirely. The "HTOOL assembly impractical at scale" caveat does **not** hold on theo3.
3. **HTOOL keeps improving to np=48** (7.10→6.50 s); **HACApK regresses mildly** there
   (9.17→11.5 s). The dramatic np=48 "regression"/"collapse" in an earlier version of this
   note was a **contended-machine artifact** (a runaway job sharing the node), not NUMA
   saturation — corrected after clean re-measurement. Dense keeps improving to np=48 but is
   ~9× slower than HTOOL there.
4. **matvec @ 0.5 km, np=24**: HTOOL 1.10 ms, HACApK 1.58 ms, dense 10.7 ms.

## Recommended default on theo3
`-use_hmatrix 1` (HTOOL), np≈24, NUMA binding on. (rsf_solve's compiled default backend is
unchanged — this is a per-machine recommendation, since the ranking flipped vs walter.)

## HTOOL tuning (1 km, np=24) — already near-optimal

| eta / eps | total_s | assembly_s | matvec_ms | compression× |
|-----------|--------:|-----------:|----------:|-------------:|
| 100 / 1e-4 (default) | 0.526 | 0.25 | 0.102 | 3.38 |
| 10 / 1e-4 | 0.566 | 0.27 | 0.113 | 3.21 |
| 30 / 1e-4 | 0.538 | 0.26 | 0.106 | 3.32 |
| 300 / 1e-4 | 0.523 | 0.26 | 0.101 | 3.40 |
| 100 / **1e-3** | **0.454** | 0.19 | 0.097 | 4.37 |
| 10 / 1e-3 | 0.491 | 0.21 | 0.106 | 4.12 |

- **`eta` is a null lever** for this thin-planar-fault geometry (10→300 within noise).
- **`epsilon` 1e-4→1e-3** gives ~14% on a short (assembly-weighted) run, ~5% matvec on a long
  one. **Accuracy-safe**: anchor-gated at 2 km, recurrence 236.8119 (Δ0.001 vs golden,
  Δ0.0019 vs published) — the ODE rtol=1e-4 floor still dominates even at eps=1e-3. Use it as a
  per-problem tuning knob (`-mat_htool_epsilon 1e-3`); not promoted to a compiled default since
  the safe relaxation is problem-dependent.
- **Conclusion: HTOOL on theo3 is near-optimally tuned** — no large per-matvec headroom remains
  beyond the rank-binding already banked (v0.2.0).

## Open questions from rsf_solve.md — resolved for theo3

- *"compress_interaction_matrix vs rsf_solve discrepancy"* (HTOOL vs HACApK ranking): consistent
  here — on theo3 HTOOL wins, matching the microbenchmark's HTOOL-favoring; the walter rsf_solve
  result was the outlier (slow SVD assembly + that machine/build).
- *"long-run HACApK↔HTOOL crossover"*: no crossover on theo3 — HTOOL is faster at **both**
  assembly (18.7 s vs 21 s @0.5 km) **and** matvec (1.10 ms vs 1.58 ms @ np=24), so it wins for
  short *and* long runs. The extrapolated crossover was a walter artifact.
