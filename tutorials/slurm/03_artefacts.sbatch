#!/bin/bash
#SBATCH --account=ecg_general
#SBATCH --job-name=hrd_artefacts
#SBATCH --partition=short
#SBATCH --cpus-per-task=16
#SBATCH --mem=128g
#SBATCH --time=02:00:00
#SBATCH --output=logs/artefacts_%j.out
#SBATCH --error=logs/artefacts_%j.err

# Turn the fitted models into the bundle that ships with the repository, then
# draw the figures from it.
#
# Submitted rather than run on the frontend because it holds two or three
# hundred MB of draws in memory at a time and calls posterior_epred() and
# posterior_predict() over grids of tens of thousands of rows.
#
# 03 skips models whose fit is missing and 04 skips figures whose inputs are
# missing, so this can be run against a partially completed array and re-run
# later to fill in the rest.

set -euo pipefail

PROJECT_ROOT=/faststorage/project/ecg_general/hrd_tutorial
cd "$PROJECT_ROOT"

source "$PROJECT_ROOT/env.sh"

export HRD_DATA=$PROJECT_ROOT/data/model_data.rds
export HRD_OUT=$PROJECT_ROOT/results
export HRD_SMALL=$PROJECT_ROOT/results/small
export HRD_FIGS=$PROJECT_ROOT/results/small/figures
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

# ggdist and patchwork are not in the conda environment and are not on
# conda-forge under those names. Both are plain R packages, so CRAN is fine.
Rscript -e '
  for (p in c("ggdist", "patchwork")) {
    if (!requireNamespace(p, quietly = TRUE))
      install.packages(p, repos = "https://cloud.r-project.org")
    else message(p, " already installed")
  }
'

echo "=== artefacts: $(date --iso-8601=seconds) ==="
Rscript R/03_artefacts.R

echo "=== summarise: $(date --iso-8601=seconds) ==="
Rscript R/02_summarise.R

echo "=== figures: $(date --iso-8601=seconds) ==="
Rscript R/04_figures.R

# Verify by content. A completed job that wrote nothing is the failure mode
# these scripts are most likely to have, because all three skip missing inputs
# quietly by design.
SMALL=$PROJECT_ROOT/results/small
N=$(find "$SMALL" -name '*.csv.gz' | wc -l)
P=$(find "$SMALL" -name '*.png' | wc -l)
echo "artefacts: $N csv.gz, $P png"
if [ "$N" -eq 0 ] || [ "$P" -eq 0 ]; then
  echo "ERROR: expected both tables and figures under $SMALL" >&2
  exit 1
fi
du -sh "$SMALL"
find "$SMALL" -type f -printf '%10s  %p\n' | sort -k2
