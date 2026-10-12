#!/bin/bash
#SBATCH --job-name=tempo_trash_v35
#SBATCH --partition=rtx3090
#SBATCH --exclude=quant,jelly
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=01:30:00
#SBATCH --output=/storage/always216/ROBOT/tempo_viz_20261004/logs/v35trash_%j.log
# Trash split, % labels (v33), idle pre-roll trimmed so the first frame is the policy start: frame 80 = policy 0.128 s
# (v20 trim 2.667 s showed 0.1 s on the first frame) -> cut 77 frames (2.567 s): first frame ~0.03 s, shown as 0.0 s.
set -euo pipefail
O=/storage/always216/ROBOT/tempo_viz_20261004; P=$O/page_v33
export PYTHONPATH=$O/pylib TEMPO_VIZ_FONTS=$O/fonts OMP_NUM_THREADS=8 OPENCV_NUM_THREADS=8
cd /home/always216/ROBOT/analysis/tempo_viz_20261004
A="407,187,607,413;1033,420,1207,580;1047,573,1280,720"
/home/always216/miniconda3/bin/python -u v12_landscape.py --stem $O/pc2_logs/20260930/trash_ours_tempo2_demo/v3_20260930_055207 --clip $O/drive/trash_ours.mp4 --lag0 -2.5 --trim-start 2.567 --scale 1.0 --miss-gestures 10 --segments B --anchor-lock "$A" --split --gauge --rate-log $P/trash_rate.json --out $P/trash_split_silent
date
