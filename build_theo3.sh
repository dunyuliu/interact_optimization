#!/usr/bin/env bash
#
# build_theo3.sh -- reproducible build of rsf_solve (+ HACApK / HTOOL / dense
#                   H-matrix backends) on the UTIG `theo3` node.
#
# theo3 differs from the `walter` setup the other docs assume:
#   * PETSc 3.22.5 (with htool + h2opus) lives in Dave May's tree, and its
#     MPI wrappers are under $PETSC_ARCH/bin, NOT $PETSC_DIR/build/bin.
#   * hmmvp's MPI library (libhmmvp_mpi.a) is not built here, so this build
#     disables hmmvp (-use_hmatrix 4). dense(0), HTOOL(1), h2opus(2), HACApK(3)
#     are all available.
#
# Usage:  bash build_theo3.sh        # builds eispack, HACApK C-iface, rsf_solve
#         source build_theo3.sh      # additionally leaves PETSc env exported
# ---------------------------------------------------------------------------
set -u

export PETSC_DIR=/home/utig5/dmay/software/petsc-3.22.5
export PETSC_ARCH=arch-linux-opt-theo
export PATH=$PETSC_DIR/$PETSC_ARCH/bin:$PATH
export LD_LIBRARY_PATH=$PETSC_DIR/$PETSC_ARCH/lib:${LD_LIBRARY_PATH:-}
# H-matrix backends are bandwidth-bound; pin BLAS/OpenMP to 1 thread so MPI
# rank counts are the only parallelism knob (matches the scaling protocol).
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}

REPO="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
MPIBIN=$PETSC_DIR/$PETSC_ARCH/bin

# Only build if not being sourced purely for the environment.
if [ "${1:-build}" = "build" ]; then
  echo ">> eispack (libmyeis.a)"
  make -C "$REPO/eispack" || { echo "eispack build FAILED"; return 1 2>/dev/null || exit 1; }

  echo ">> HACApK C interface (libhacapk.a)"
  mkdir -p "$REPO/HACApK/v.1.0.0/C_interface/objects"
  make -C "$REPO/HACApK/v.1.0.0/C_interface" MPIDIR="$MPIBIN" libhacapk.a \
    || { echo "HACApK build FAILED"; return 1 2>/dev/null || exit 1; }

  echo ">> rsf_solve (hmmvp disabled)"
  make -C "$REPO" obj_directories >/dev/null 2>&1
  make -C "$REPO" -j8 bin/rsf_solve \
       HMMVP_DEFINES= HMMVP_LIBS= HMMVP_OBJS= HMMVP_INC= \
    || { echo "rsf_solve build FAILED"; return 1 2>/dev/null || exit 1; }

  echo ">> done: $REPO/bin/rsf_solve"
  ls -l "$REPO/bin/rsf_solve"
fi

# Convenience for the benchmark script (it expects $PETSC_DIR/build/bin/mpirun;
# on theo3 use the arch bin instead):
export MPIRUN=$MPIBIN/mpirun
