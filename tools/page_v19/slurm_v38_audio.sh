#!/bin/bash
#SBATCH --job-name=tempo_audio_v38
#SBATCH --partition=rtx3090
#SBATCH --exclude=quant,jelly
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:40:00
#SBATCH --output=/storage/always216/ROBOT/tempo_viz_20261004/logs/v38audio_%j.log
set -euo pipefail
O=/storage/always216/ROBOT/tempo_viz_20261004; P=$O/page_v33; Q=$O/page_v38; mkdir -p $Q
FF=$O/pylib/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2
cd /home/always216/ROBOT/analysis/tempo_viz_20261004
for N in cup towel trash; do for M in firebird maserati; do
  /home/always216/ROBOT/droid_umi_dtw/.venv/bin/python -u v36_tempo_audio.py $P/${N}_rate.json $P/${N}_split_silent.mp4 $Q/${N}_split_$M.mp4 --mode engine --engine $M
done; done
for M in firebird maserati; do $FF -v error -y -i $Q/trash_split_$M.mp4 -c:v libx264 -crf 30 -preset medium -c:a copy -movflags +faststart $Q/trash_split_${M}_preview.mp4; done
date
