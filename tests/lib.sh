#!/usr/bin/env bash
# tests/lib.sh -- shared environment + the canonical BP5 anchor invocation.
#
# Single source of truth for "the anchor case" so every test (smoke, physics,
# backend-equivalence, perf) drives the *identical* physics and only varies
# backend / np / stop_time. Sourced by run_anchor.sh.
#
# theo3 env (see ../build_theo3.sh). Override any var from the environment.
# ---------------------------------------------------------------------------
export PETSC_DIR=${PETSC_DIR:-/home/utig5/dmay/software/petsc-3.22.5}
export PETSC_ARCH=${PETSC_ARCH:-arch-linux-opt-theo}
export LD_LIBRARY_PATH=$PETSC_DIR/$PETSC_ARCH/lib:${LD_LIBRARY_PATH:-}
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}

REPO=${REPO:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}
RB=${RB:-$REPO/bin/rsf_solve}
BP5=${BP5:-$REPO/bp5}
MPIRUN=${MPIRUN:-$PETSC_DIR/$PETSC_ARCH/bin/mpirun}
# NUMA-aware rank binding, on by default as standard HPC hygiene. Measured ~neutral
# on theo3 (0-12% at np=48, within noise) — not a speedup. Harmless at np=1.
BIND=${BIND:--bind-to core -map-by numa}

# Anchor resolution. 2km/1000 cells: fast (~seconds), and still reproduces the
# real physics — first spontaneous recurrence at 236.81 yr (matches HBI + the
# published BEM cluster). The golden was blessed from a -use_hmatrix 0 (dense)
# run at this resolution; dense is the exact ground truth.
RES=${RES:-2km}

# backend tag -> rsf_solve H-matrix flags  (must match bp5/bench_hmatrix.sh)
anchor_flags_for() {
  case "$1" in
    dense)  echo "-use_hmatrix 0" ;;
    htool)  echo "-use_hmatrix 1 -mat_htool_epsilon ${HEPS:-1e-4}" ;;
    h2opus) echo "-use_hmatrix 2" ;;
    hacapk) echo "-use_hmatrix 3 -hacapk_ztol ${ZTOL:-1e-4}" ;;
    *) echo "ERROR: unknown backend '$1'" >&2; return 1 ;;
  esac
}

# run_anchor <backend> <np> <stop_yr> <outdir>
# Runs the canonical BP5 case into <outdir> (created fresh). Writes
# rsf_monitor.dat / rsf_events.dat there. Echoes the run log path.
run_anchor() {
  local be=$1 np=$2 stop=$3 out=$4
  local geom=$BP5/geom_bp5_${RES}.in rsf=$BP5/rsf_bp5_${RES}.dat
  local ic=$BP5/ic_bp5_${RES}.in dc=$BP5/dc_bp5_${RES}.in
  rm -rf "$out"; mkdir -p "$out"
  ( cd "$out" && $MPIRUN $BIND -np "$np" "$RB" \
      -geom_file "$geom" -rsf_file "$rsf" -rsf_ic_file "$ic" -rsf_dc_file "$dc" \
      $(anchor_flags_for "$be") \
      -shear_modulus 3.204e10 -s_wave_speed 3464 \
      -f0 0.6 -dc 0.14 -vpl 1e-9 -v0 1e-6 -sigma_init 25e6 \
      -rtol ${RTOL:-1e-4} -stop_time_yr "$stop" -ts_max_steps 2000000 \
      -print_interval_yr 0.05 -log_view > run.log 2>&1 )
  echo "$out/run.log"
}
