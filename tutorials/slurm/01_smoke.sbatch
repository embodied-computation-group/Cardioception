#!/bin/bash
#SBATCH --account=ecg_general
#SBATCH --job-name=hrd_smoke
#SBATCH --partition=short
#SBATCH --cpus-per-task=16
#SBATCH --mem=32g
#SBATCH --time=03:00:00
#SBATCH --output=logs/smoke_%j.out
#SBATCH --error=logs/smoke_%j.err

# Rehearse the whole pipeline on a handful of subjects before committing a node
# for a day.
#
# The setup job's smoke test only proves CmdStan compiles and samples. This one
# exercises what actually breaks: the formulas in models.R, the prior
# verification, the aggregation and coding checks in 00_prepare.R, and the
# post-processing in 02_summarise.R.
#
# Writes into results_smoke/ so it can never be mistaken for, or collide with,
# the real fits. Nothing from this run is reportable.

set -euo pipefail

PROJECT_ROOT=/faststorage/project/ecg_general/hrd_tutorial
cd "$PROJECT_ROOT"
source "$PROJECT_ROOT/env.sh"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

echo "=== smoke test on $(hostname), started $(date --iso-8601=seconds) ==="

# --- 1. data preparation ---------------------------------------------------
# Runs on the full dataset: it is cheap, and the coding checks inside it are
# exactly what we want exercised.
Rscript R/00_prepare.R data/hrd_tutorial.csv data/model_data.rds
test -s data/model_data.rds || { echo "ERROR: model_data.rds not written" >&2; exit 1; }

# --- 1b. prior predictive --------------------------------------------------
# Check what the priors claim before any data is involved. Cheap, and the only
# way the prior choices are verified rather than asserted.
HRD_OUT=$PROJECT_ROOT/results_smoke HRD_FIGS=$PROJECT_ROOT/results_smoke/figures   Rscript R/00b_prior_predictive.R psy_full

# --- 2. one model of each kind, cut down -----------------------------------
export HRD_DATA=$PROJECT_ROOT/data/model_data.rds
export HRD_OUT=$PROJECT_ROOT/results_smoke
export HRD_MAX_SUBJ=25
export HRD_CHAINS=2
export HRD_THREADS=4
export HRD_ITER=600
export HRD_WARMUP=300

# psy_full exercises the interaction terms and every prior path. meta_full
# exercises the ordbetareg branch, which shares none of that code.
for MODEL in psy_full meta_full; do
  echo "--- smoke: $MODEL ---"
  Rscript R/01_fit.R "$MODEL"
  SUMMARY="$HRD_OUT/${MODEL}_summary.csv"
  if [ ! -s "$SUMMARY" ]; then
    echo "ERROR: $SUMMARY missing or empty" >&2
    exit 1
  fi
  echo "$MODEL summary has $(wc -l < "$SUMMARY") lines"
done

# --- 3. post-processing ----------------------------------------------------
HRD_OUT=$PROJECT_ROOT/results_smoke \
HRD_FIGS=$PROJECT_ROOT/results_smoke/figures \
  Rscript R/02_summarise.R

# --- 4. verify by content --------------------------------------------------
echo "--- produced ---"
find "$PROJECT_ROOT/results_smoke" -type f -printf '%10s  %p\n' | sort -k2

for f in "$PROJECT_ROOT/results_smoke/contrasts.csv" \
         "$PROJECT_ROOT/results_smoke/figures/fig_effects.png" \
         "$PROJECT_ROOT/results_smoke/figures/fig_confidence.png"; do
  if [ ! -s "$f" ]; then
    echo "ERROR: expected artefact missing or empty: $f" >&2
    exit 1
  fi
done

echo "SMOKE_OK  $(date --iso-8601=seconds)"
