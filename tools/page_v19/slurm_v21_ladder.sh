#!/bin/bash
#SBATCH --job-name=tempo_ladder
#SBATCH --partition=rtx3090
#SBATCH --exclude=quant,jelly
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=00:40:00
#SBATCH --array=0-2
#SBATCH --output=/storage/always216/ROBOT/tempo_viz_20261004/logs/ladder_%A_%a.log
set -euo pipefail
O=/storage/always216/ROBOT/tempo_viz_20261004; mkdir -p $O/page_v21
export PYTHONPATH=$O/pylib TEMPO_VIZ_FONTS=$O/fonts OMP_NUM_THREADS=4
cd /home/always216/ROBOT/analysis/tempo_viz_20261004
T=(cup towel trash); N=${T[$SLURM_ARRAY_TASK_ID]}
/home/always216/miniconda3/bin/python -u v30_baseline_ladder.py $N $O/page_v21/${N}_ladder.mp4
