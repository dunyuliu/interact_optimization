# Golden + external reference provenance

## Golden files (self-consistency anchor)

- `bp5_2km_dense.events`, `bp5_2km_dense.monitor`

Blessed from a `rsf_solve -use_hmatrix 0` (dense, exact) run of the BP5-QD 2 km
case (`bp5/*_2km.*`) to 245 yr, `-rtol 1e-4`, `-print_interval_yr 0.05`, on theo3
(PETSc 3.22.5, `-Ofast -march=native`). Dense is the ground truth; HACApK/HTOOL
are validated against it.

First spontaneous recurrence in the golden: **236.8130 yr**.

## External reference (independent validation)

| quantity | value | source |
|----------|-------|--------|
| BP5-QD recurrence, 2 km | **236.81 yr** | HBI (lattice-H, patched); interact matches exactly — `bp5/README.md` §4 |
| BP5-QD recurrence, 1 km | 234.28 yr (HBI) / 234.29 (interact) | `bp5/README.md` §4 |
| published inter-event time | ~235 yr (BEM cluster) | Jiang et al. 2022, *JGR Solid Earth*, doi:10.1029/2021JB023519, Fig. 9a |
| rupture duration | ~30 s | Jiang et al. 2022 |
| stress drop | ~5 MPa (surface) / ~10 MPa (VW core) | Jiang et al. 2022 |
| peak slip rate | ~1 m/s | Jiang et al. 2022 |

`run_anchor.sh physics` validates the computed recurrence against the 236.81 yr
HBI/published value (`--ref-recurrence`), not only against the self-golden.
