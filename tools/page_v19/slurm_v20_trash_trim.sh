#!/bin/bash
#SBATCH --job-name=tempo_trash_trim
#SBATCH --partition=rtx3090
#SBATCH --exclude=quant,jelly
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=01:30:00
#SBATCH --array=0-1
#SBATCH --output=/storage/always216/ROBOT/tempo_viz_20261004/logs/v20trash_%A_%a.log
# Trash with the idle pre-roll trimmed (clip starts when the arm starts moving: log 0.131 s = clip 2.670 s -> frame 80).
set -euo pipefail
O=/storage/always216/ROBOT/tempo_viz_20261004; P=$O/page_v19
export PYTHONPATH=$O/pylib TEMPO_VIZ_FONTS=$O/fonts OMP_NUM_THREADS=8 OPENCV_NUM_THREADS=8
cd /home/always216/ROBOT/analysis/tempo_viz_20261004
PY=/home/always216/miniconda3/bin/python
A="407,187,607,413;1033,420,1207,580;1047,573,1280,720"
TR="--stem $O/pc2_logs/20260930/trash_ours_tempo2_demo/v3_20260930_055207 --clip $O/drive/trash_ours.mp4 --lag0 -2.5 --trim-start 2.667 --scale 1.0 --miss-gestures 10 --segments B --anchor-lock $A"
case $SLURM_ARRAY_TASK_ID in
  0) $PY -u v12_landscape.py $TR --split --gauge --rate-log $P/trash_rate.json --out $P/trash_split_silent
     $PY -u v27_engine_audio.py $P/trash_rate.json $P/trash_split_silent.mp4 $P/trash_split.mp4 ;;
  1) $PY -u v12_landscape.py $TR --no-focus --ghost-register --out $O/trash_055207_zilean_v20B_trim ;;
esac
date
