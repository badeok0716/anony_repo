#!/bin/bash
#SBATCH --job-name=tempo_split_v33
#SBATCH --partition=rtx3090
#SBATCH --exclude=quant,jelly
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=01:30:00
#SBATCH --array=0-2
#SBATCH --output=/storage/always216/ROBOT/tempo_viz_20261004/logs/v33split_%A_%a.log
# Page (2026-10-11): v18 split + speedometer on the ours video (v26) + engine sound track from the displayed rate (v27).
set -euo pipefail
O=/storage/always216/ROBOT/tempo_viz_20261004; P=$O/page_v33; mkdir -p $P
export PYTHONPATH=$O/pylib TEMPO_VIZ_FONTS=$O/fonts OMP_NUM_THREADS=8 OPENCV_NUM_THREADS=8
cd /home/always216/ROBOT/analysis/tempo_viz_20261004
PY=/home/always216/miniconda3/bin/python
A="407,187,607,413;1033,420,1207,580;1047,573,1280,720"
case $SLURM_ARRAY_TASK_ID in
  0) N=trash; $PY -u v12_landscape.py --stem $O/pc2_logs/20260930/trash_ours_tempo2_demo/v3_20260930_055207 --clip $O/drive/trash_ours.mp4 --lag0 -2.5 --scale 1.0 --miss-gestures 10 --segments B --anchor-lock "$A" --split --gauge --rate-log $P/trash_rate.json --out $P/trash_split_silent
     V=$P/trash_split_silent.mp4 ;;
  1) N=cup; $PY -u v08_zilean4.py --task cup --stem $O/pc2_logs/20260929/cup_ours_tempo2_demo/v3_20260929_041209 --web $O/page_videos/web_cup.mp4 --camera $O/cup_041209_camera.json --orig $O/orig/cup_sdr30.mp4 --orig-affine 0.37533,-0.05,1.6 --segments B --split --gauge --rate-log $P/cup_rate.json --out $P/cup_split_silent.mp4
     V=$P/cup_split_silent.mp4 ;;
  2) N=towel; $PY -u v08_zilean4.py --task towel --stem $O/pc2_logs/20260929/towel_ours_tempo1_demo/v3_20260929_061007 --web $O/page_videos/web_towel.mp4 --camera $O/towel_061007_camera.json --orig $O/orig/towel_30.mp4 --orig-affine 0.5631,-0.14,-0.46 --segments B --split --gauge --rate-log $P/towel_rate.json --out $P/towel_split_silent.mp4
     V=$P/towel_split_silent.mp4 ;;
esac
for M in supercar clock; do /home/always216/ROBOT/droid_umi_dtw/.venv/bin/python -u v33_tempo_audio.py $P/${N}_rate.json $V $P/${N}_split_$M.mp4 --mode $M; done
date
