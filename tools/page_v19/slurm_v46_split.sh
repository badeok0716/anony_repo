#!/bin/bash
#SBATCH --job-name=tempo_split_v46
#SBATCH --partition=rtx3090
#SBATCH --exclude=quant,jelly
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=00:40:00
#SBATCH --array=0-1
#SBATCH --output=/storage/always216/ROBOT/tempo_viz_20261004/logs/v46split_%A_%a.log
# Cup/towel split videos starting at the policy start (0.0 s), first frame held until the recording starts (cup 0.264 s,
# towel 0.451 s), then the final engine sound (v45, Ferrari F355 rpm = dial).
set -euo pipefail
O=/storage/always216/ROBOT/tempo_viz_20261004; P=$O/page_v46; mkdir -p $P
export PYTHONPATH=$O/pylib TEMPO_VIZ_FONTS=$O/fonts OMP_NUM_THREADS=8 OPENCV_NUM_THREADS=8
cd /home/always216/ROBOT/analysis/tempo_viz_20261004
PY=/home/always216/miniconda3/bin/python
case $SLURM_ARRAY_TASK_ID in
  0) N=cup; $PY -u v08_zilean4.py --task cup --stem $O/pc2_logs/20260929/cup_ours_tempo2_demo/v3_20260929_041209 --web $O/page_videos/web_cup.mp4 --camera $O/cup_041209_camera.json --orig $O/orig/cup_sdr30.mp4 --orig-affine 0.37533,-0.05,1.6 --segments B --split --gauge --start-at-policy --rate-log $P/cup_rate.json --out $P/cup_split_silent.mp4 ;;
  1) N=towel; $PY -u v08_zilean4.py --task towel --stem $O/pc2_logs/20260929/towel_ours_tempo1_demo/v3_20260929_061007 --web $O/page_videos/web_towel.mp4 --camera $O/towel_061007_camera.json --orig $O/orig/towel_30.mp4 --orig-affine 0.5631,-0.14,-0.46 --segments B --split --gauge --start-at-policy --rate-log $P/towel_rate.json --out $P/towel_split_silent.mp4 ;;
esac
/home/always216/ROBOT/droid_umi_dtw/.venv/bin/python -u v45_f355_rpm.py $P/${N}_rate.json $P/${N}_split_silent.mp4 $P/${N}_split.mp4
date
