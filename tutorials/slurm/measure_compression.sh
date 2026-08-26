#!/bin/bash
# Measure what a general-purpose compressor can and cannot do to a fitted model.
# Run under srun, not on the frontend: xz on a few hundred MB is real work.
set -euo pipefail
cd /faststorage/project/ecg_general/hrd_tutorial/results
F=psy_intero.rds
echo "file        $F"
echo "gzip_MB     $(echo "scale=1; $(stat -c %s $F)/1048576" | bc)"
RAW=$(zcat "$F" | wc -c)
echo "raw_MB      $(echo "scale=1; $RAW/1048576" | bc)"
XZ=$(zcat "$F" | xz -6 -T16 -c | wc -c)
echo "xz_MB       $(echo "scale=1; $XZ/1048576" | bc)"
echo "xz_vs_gzip  $(echo "scale=3; $XZ/$(stat -c %s $F)" | bc)"
