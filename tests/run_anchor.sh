#!/usr/bin/env bash
#
# run_anchor.sh -- regression / correctness / performance anchor for rsf_solve.
#
# The anchor that lets you optimize safely: any change to a backend, the
# integrator, the kernels, or the build must still reproduce the BP5 physics
# (recurrence + slip-velocity trace) to tolerance, or this fails loudly.
#
#   ./run_anchor.sh smoke   [backends...]   # ~seconds: trace to 50 yr, all backends agree
#   ./run_anchor.sh physics [backends...]   # ~10-30 s: full cycle, recurrence = 236.81 yr
#   ./run_anchor.sh perf    [backends...] [nplist]   # timings vs the committed baseline
#   ./run_anchor.sh all                     # smoke + physics  (default backends)
#
# Default backends: dense hacapk htool.  Exit code is nonzero if any tier fails.
# Re-bless the golden (only after a deliberate, verified physics change):
#   ./run_anchor.sh bless
# ---------------------------------------------------------------------------
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib.sh"
GOLD="$HERE/golden"
WORK="${WORK:-$REPO/runs/anchor}"
CHECK="python3 $HERE/check_anchor.py"
mkdir -p "$WORK"

[ -x "$RB" ] || { echo "FATAL: $RB not found -- build first (bash $REPO/build_theo3.sh)"; exit 2; }

rc=0
banner(){ printf '\n=== %s ===\n' "$*"; }

tier_smoke(){   # fast trace check, every backend vs golden (no event in window)
  local bes="${1:-dense hacapk htool}"
  banner "SMOKE  (2km, 50 yr, trace vs golden)"
  for be in $bes; do
    local mode=regression; [ "$be" = dense ] || mode=equiv
    echo "[$be]"; run_anchor "$be" 1 50 "$WORK/smoke_$be" >/dev/null
    $CHECK --run "$WORK/smoke_$be" --golden "$GOLD" --window 50 --mode "$mode" --no-event || rc=1
  done
}

tier_inputs(){  # verify BP5 inputs against the published spec + regeneration
  banner "INPUTS (BP5 ${RES} spec conformance + regeneration)"
  local ds=2.0; [ "$RES" = 1km ] && ds=1.0; [ "$RES" = 0.5km ] && ds=0.5
  python3 "$HERE/check_inputs.py" --repo "$REPO" --ds "$ds" || rc=1
}

# Published / HBI reference recurrence [yr] for the external-validation check.
REF_RECUR=${REF_RECUR:-236.81}   # 2km BP5: HBI 236.81, published BEM cluster

tier_physics(){ # full cycle: recurrence + final state vs golden AND vs published
  local bes="${1:-dense hacapk htool}"
  banner "PHYSICS (2km, 245 yr, recurrence + trace + final slip; vs golden & published)"
  for be in $bes; do
    local mode=regression; [ "$be" = dense ] || mode=equiv
    echo "[$be]"; run_anchor "$be" 1 245 "$WORK/phys_$be" >/dev/null
    $CHECK --run "$WORK/phys_$be" --golden "$GOLD" --window all --mode "$mode" \
           --trace info --ref-recurrence "$REF_RECUR" --ref-tol 0.1 || rc=1
  done
}

tier_perf(){    # timings: assembly / matvec / total, vs committed baseline CSV
  local bes="${1:-dense hacapk htool}" nplist="${2:-1 2 4}"
  banner "PERF   (2km, 50 yr, -log_view timings)"
  printf "%-8s %4s %10s %11s %11s %8s\n" backend np total_s assembly_s matvec_ms nsteps
  local csv="$WORK/perf_2km.csv"; echo "backend,np,total_s,assembly_s,matvec_ms,nsteps" > "$csv"
  for be in $bes; do for np in $nplist; do
    local log; log=$(run_anchor "$be" "$np" 50 "$WORK/perf_${be}_np${np}")
    local total asm mm_c mm_t mv ts_t nst
    total=$(awk '/Time \(sec\):/{print $3; exit}' "$log")
    read mm_c mm_t < <(awk '/^MatMult /{print $2,$4; exit}' "$log")
    read nst ts_t  < <(awk '/^TSStep /{print $2,$4; exit}' "$log")
    asm=$(awk -v t="${total:-0}" -v s="${ts_t:-0}" 'BEGIN{printf "%.2f",t-s}')
    mv=$(awk -v t="${mm_t:-0}" -v c="${mm_c:-0}" 'BEGIN{printf (c>0)?"%.3f":"NA",(c>0)?t/c*1000:0}')
    printf "%-8s %4s %10s %11s %11s %8s\n" "$be" "$np" "${total:-NA}" "$asm" "$mv" "${nst:-NA}"
    echo "$be,$np,${total:-NA},$asm,$mv,${nst:-NA}" >> "$csv"
  done; done
  echo "wrote $csv"
}

tier_bless(){
  banner "BLESS  (regenerate golden from dense, 245 yr)"
  read -p "Overwrite golden with current dense build output? [y/N] " ok
  [ "$ok" = y ] || { echo "aborted"; return 0; }
  run_anchor dense 1 245 "$WORK/bless" >/dev/null
  cp "$WORK/bless/rsf_events.dat"  "$GOLD/bp5_2km_dense.events"
  cp "$WORK/bless/rsf_monitor.dat" "$GOLD/bp5_2km_dense.monitor"
  echo "re-blessed: $GOLD"
}

case "${1:-all}" in
  inputs)  tier_inputs;;
  smoke)   shift; tier_smoke "$*";;
  physics) shift; tier_physics "$*";;
  perf)    tier_perf "${2:-}" "${3:-}";;
  bless)   tier_bless;;
  all)     tier_inputs; tier_smoke "dense hacapk htool"; tier_physics "dense hacapk htool";;
  *) echo "usage: $0 {inputs|smoke|physics|perf|all|bless} [backends] [nplist]"; exit 2;;
esac

banner "$([ $rc -eq 0 ] && echo 'ALL ANCHORS PASS' || echo 'ANCHOR FAILURE')"
exit $rc
