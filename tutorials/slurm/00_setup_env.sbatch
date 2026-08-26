#!/bin/bash
#SBATCH --account=ecg_general
#SBATCH --job-name=hrd_setup
#SBATCH --partition=short
#SBATCH --cpus-per-task=16
#SBATCH --mem=32g
#SBATCH --time=06:00:00
#SBATCH --output=logs/setup_%j.out
#SBATCH --error=logs/setup_%j.err

# Bootstrap R, brms and CmdStan into project storage.
#
# GenomeDK has no R, no module system and no preinstalled conda, so everything is
# installed from scratch. This follows the platform's documented approach
# (https://genome.au.dk/docs/installing-software/): install Miniforge, and never
# install anything into the base environment.
#
# Submitted rather than run on the login node because building CmdStan compiles a
# fair amount of C++. Idempotent: re-running skips whatever is already present.
#
# Note on `set -u`: conda's own activate.d hooks reference variables before
# setting them, so nounset has to come off around any activation.

set -euo pipefail

PROJECT_ROOT=/faststorage/project/ecg_general/hrd_tutorial
FORGE=$PROJECT_ROOT/miniforge
ENV_PREFIX=$PROJECT_ROOT/envs/hrd

mkdir -p "$PROJECT_ROOT"/{logs,data,results,R,slurm,envs}
cd "$PROJECT_ROOT"

# --- Miniforge -------------------------------------------------------------
if [ ! -x "$FORGE/bin/conda" ]; then
  echo "[setup] installing Miniforge into project storage"
  curl -Ls -o /tmp/miniforge_$$.sh \
    https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
  bash /tmp/miniforge_$$.sh -b -p "$FORGE"
  rm -f /tmp/miniforge_$$.sh
  # The docs are explicit that base must stay clean.
  "$FORGE/bin/conda" config --set auto_activate_base false
else
  echo "[setup] Miniforge already present"
fi

set +u
source "$FORGE/etc/profile.d/conda.sh"
set -u

# --- environment -----------------------------------------------------------
# A named prefix under the project, never base. r-ordbetareg is not on
# conda-forge, so it comes from CRAN below.
if [ ! -d "$ENV_PREFIX" ]; then
  echo "[setup] creating environment at $ENV_PREFIX"
  mamba create -y -p "$ENV_PREFIX" -c conda-forge \
    r-base=4.4 \
    r-brms \
    r-cmdstanr \
    r-posterior \
    r-bayesplot \
    r-tidyverse \
    r-marginaleffects \
    r-remotes \
    cmdstan \
    compilers \
    make
else
  echo "[setup] environment already present"
fi

set +u
conda activate "$ENV_PREFIX"
set -u

# The conda cmdstan package sets CMDSTAN in its activation hook. Only go looking
# for it if that did not happen.
CMDSTAN_PATH="${CMDSTAN:-}"
if [ -z "$CMDSTAN_PATH" ]; then
  CMDSTAN_PATH=$(ls -d "$ENV_PREFIX"/bin/cmdstan 2>/dev/null || true)
fi
if [ -z "$CMDSTAN_PATH" ]; then
  CMDSTAN_PATH=$(ls -d "$ENV_PREFIX"/opt/cmdstan* 2>/dev/null | head -1 || true)
fi
echo "[setup] CMDSTAN=$CMDSTAN_PATH"
export CMDSTAN="$CMDSTAN_PATH"

# env.sh is sourced by jobs that run with `set -u`, so it lifts nounset for the
# activation and restores whatever the caller had.
cat > "$PROJECT_ROOT/env.sh" <<ENVEOF
# Source this before running anything R here.
__hrd_had_u=0
case \$- in *u*) __hrd_had_u=1 ;; esac
set +u
source $FORGE/etc/profile.d/conda.sh
conda activate $ENV_PREFIX
export CMDSTAN="\${CMDSTAN:-$CMDSTAN_PATH}"
if [ "\$__hrd_had_u" = 1 ]; then set -u; fi
unset __hrd_had_u
ENVEOF
echo "[setup] wrote env.sh"

# --- packages not on conda-forge -------------------------------------------
Rscript -e '
  if (!requireNamespace("ordbetareg", quietly = TRUE)) {
    install.packages("ordbetareg", repos = "https://cloud.r-project.org")
  } else {
    message("ordbetareg already installed")
  }
'

# --- verify by content, not by exit code -----------------------------------
Rscript -e '
  suppressPackageStartupMessages({
    library(brms); library(cmdstanr); library(ordbetareg)
  })
  cat("brms       ", as.character(packageVersion("brms")), "\n")
  cat("cmdstanr   ", as.character(packageVersion("cmdstanr")), "\n")
  cat("ordbetareg ", as.character(packageVersion("ordbetareg")), "\n")
  cat("CMDSTAN    ", Sys.getenv("CMDSTAN"), "\n")
  cat("cmdstan ver", cmdstanr::cmdstan_version(), "\n")

  # Compile and sample a trivial model with threading on. If the toolchain or
  # reduce_sum support is broken, it fails here in seconds rather than after a
  # day in the queue.
  f <- write_stan_file("
    data { int<lower=0> N; array[N] int y; }
    parameters { real<lower=0,upper=1> theta; }
    model { y ~ bernoulli(theta); }
  ")
  m <- cmdstan_model(f, cpp_options = list(stan_threads = TRUE))
  s <- m$sample(data = list(N = 10, y = rep(0:1, 5)), chains = 2,
                threads_per_chain = 2,
                iter_warmup = 200, iter_sampling = 200, refresh = 0)
  cat("smoke test theta mean:", round(s$summary("theta")$mean, 3), "\n")
  cat("SETUP_OK\n")
'

echo "[setup] done"
