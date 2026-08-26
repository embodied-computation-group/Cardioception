#!/bin/bash
#SBATCH --account=ecg_general
#SBATCH --job-name=hrd_figures
#SBATCH --partition=short
#SBATCH --cpus-per-task=4
#SBATCH --mem=16g
#SBATCH --time=00:20:00
#SBATCH --output=logs/figures_%j.out
#SBATCH --error=logs/figures_%j.err

# Redraw the figures without touching the fitted models.
#
# R/04_figures.R reads results/small/ and nothing else, so this needs neither the
# 190-320 MB fits nor several minutes of posterior_epred. Use it for anything
# that is purely a plotting change: a label, a palette, an axis. Re-run
# 03_artefacts.sbatch only when the quantity being plotted has to change.
#
# It is small enough to run under srun interactively as well:
#   srun --account=ecg_general --mem=16g --time=00:20:00 slurm/04_figures.sbatch

set -euo pipefail

PROJECT_ROOT=/faststorage/project/ecg_general/hrd_tutorial
cd "$PROJECT_ROOT"

source "$PROJECT_ROOT/env.sh"

export HRD_SMALL=$PROJECT_ROOT/results/small
export HRD_FIGS=$PROJECT_ROOT/results/small/figures

Rscript R/04_figures.R

N=$(find "$HRD_FIGS" -name '*.png' | wc -l)
echo "figures on disk: $N"
[ "$N" -gt 0 ] || { echo "ERROR: no figures written" >&2; exit 1; }
