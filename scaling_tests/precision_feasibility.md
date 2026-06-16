# Mixed/single-precision matvec — feasibility (theo3, 2026-06)

The `rsf_solve` matvec is memory-bandwidth-bound, so halving the bytes moved
(single or mixed precision) is worth ~1.5–2× **in principle**. In practice, none of
the three production backends can be made single/mixed-precision without major work:

| backend | matvec type | single/mixed feasible? | blocker |
|---------|-------------|------------------------|---------|
| dense   | PETSc `MatDense` `MatMult` | No (here) | precision is `PetscReal`; all 4 theo3 PETSc arches are `--with-precision=double`. Needs a single-prec PETSc built from source. |
| HTOOL   | PETSc `MATHTOOL` | No (here) | same — `MATHTOOL` arithmetic is locked to `PetscReal`. |
| HACApK  | shell → bundled Fortran | Not in-session | `m_HACApK_*.f90` + `HACApK_c_interface.f90` hardcode `real*8` / `MPI_DOUBLE_PRECISION` with no KIND parameterization; the C ABI (`chacapk_mult_Ax_H`) is `REAL*8 ↔ double*`. A single/mixed port is ~5-file surgery + full parity & scaling re-validation (~2–3 days). |

Note: interact's `precision_single.h`/`precision_mixed.h` and `config/makefile.mixed`
switch `COMP_PRECISION`/`I_MATRIX_PREC` for the **legacy static interact solver only**
(`interact.c` / `calc_interaction_matrix`). `rsf_solve` fills a PETSc `Mat` via
`calc_petsc_Isn_matrices()` and never touches those macros — so the existing "mixed"
build mode gives `rsf_solve` nothing.

**Conclusion:** precision is a real but expensive lever, deferred. The accuracy budget
(ODE `rtol`=1e-4, H-matrix tol 1e-4) *would* admit a single-precision operator apply, so
the payoff is there if a single-precision PETSc arch is ever built or HACApK is ported.
GPU-free wins with better effort/reward: MPI rank pinning (done, v0.2.0-opt) and the
integrator/step-count lever (−30 to −40% matvecs, accuracy-trade decision pending).
