#!/bin/bash
#SBATCH --account=ecg_general
#SBATCH --job-name=hrd_fit
#SBATCH --partition=normal
#SBATCH --cpus-per-task=128
#SBATCH --mem=192g
#SBATCH --time=1-12:00:00
#SBATCH --array=0-3
#SBATCH --output=logs/fit_%A_%a.out
#SBATCH --error=logs/fit_%A_%a.err

# One model per array task.
#
#   0  psy_intero  minimal example, Intero only
#   1  psy_main    Modality, gender, age and BMI as main effects
#   2  psy_full    Modality by gender and age, BMI controlled
#   3  meta_full   confidence, ordered beta regression
#
# Parallelism is 8 chains x 16 threads = 128 cores. Within-chain threading
# (reduce_sum) is the useful lever here because the likelihood runs over tens of
# thousands of aggregated cells; adding chains past 8 mostly buys redundant
# samples instead of speed.
#
# Walltime is sized for the worst case. A job killed at the limit writes nothing,
# and the ones it kills are the slow-to-converge models, which is precisely the
# wrong sample to lose.
#
# Each task exits immediately if its summary already exists, so a partially
# completed array can be resubmitted unchanged to fill only the gaps.

set -euo pipefail

PROJECT_ROOT=/faststorage/project/ecg_general/hrd_tutorial
cd "$PROJECT_ROOT"

source "$PROJECT_ROOT/env.sh"

MODELS=(psy_intero psy_main psy_full meta_full)

# A one-element array reports MIN == MAX, so never derive a count from the range.
IDX=${SLURM_ARRAY_TASK_ID:-0}
if [ "$IDX" -ge "${#MODELS[@]}" ]; then
  echo "task $IDX beyond the model list, nothing to do"
  exit 0
fi
MODEL=${MODELS[$IDX]}

echo "=== task $IDX -> $MODEL on $(hostname) ==="
echo "started $(date --iso-8601=seconds)"

export HRD_DATA=$PROJECT_ROOT/data/model_data.rds
export HRD_OUT=$PROJECT_ROOT/results
export HRD_CHAINS=8
export HRD_THREADS=16
export HRD_ITER=4000
export HRD_WARMUP=2000

# Keep the BLAS to one thread per process: Stan does its own parallelism and
# nested thread pools oversubscribe the allocation.
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

Rscript R/01_fit.R "$MODEL"

echo "finished $(date --iso-8601=seconds)"

# Verify by content. SLURM reporting COMPLETED is not evidence a fit was written.
SUMMARY="$PROJECT_ROOT/results/${MODEL}_summary.csv"
if [ ! -s "$SUMMARY" ]; then
  echo "ERROR: $SUMMARY missing or empty" >&2
  exit 1
fi
echo "wrote $(wc -l < "$SUMMARY") lines to $SUMMARY"
