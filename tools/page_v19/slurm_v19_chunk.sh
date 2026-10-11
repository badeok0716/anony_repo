#!/bin/bash
#SBATCH --job-name=tempo_page_chunk
#SBATCH --partition=rtx3090
#SBATCH --exclude=quant,jelly
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/storage/always216/ROBOT/tempo_viz_20261004/logs/v19chunk_%j.log
set -euo pipefail
O=/storage/always216/ROBOT/tempo_viz_20261004
export PYTHONPATH=$O/pylib TEMPO_VIZ_FONTS=$O/fonts OMP_NUM_THREADS=8 OPENCV_NUM_THREADS=8
cd /home/always216/ROBOT/analysis/tempo_viz_20261004
/home/always216/miniconda3/bin/python -u v28_chunk_assets.py --stem $O/pc2_logs/20260929/cup_ours_tempo2_demo/v3_20260929_041209 --camera $O/cup_041209_camera.json --orig $O/orig/cup_sdr30.mp4 --orig-affine 0.37533,-0.05,1.6 --out $O/page_v19
date
