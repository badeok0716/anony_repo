"""Export existing v18 split panels and telemetry without video re-encoding."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--analysis-dir', type=Path, required=True)
    p.add_argument('--asset-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1])
    a = p.parse_args()
    sys.path.insert(0, str(a.analysis_dir))
    import numpy as np
    from v01_tempo_clock import tempo_clock
    from v25_completion import completion
    specs = [
        ('cup','20260929','cup_ours_tempo2_demo','041209','cup_041209_camera.json',2),
        ('towel','20260929','towel_ours_tempo1_demo','061007','towel_061007_camera.json',1),
        ('trash','20260930','trash_ours_tempo2_demo','055207','trash_055207_zilean_v18B_split_camera.json',2),
    ]
    result = dict(schema=1, definition='Applied tempo from v01_tempo_clock, seam-aware planned execution; not raw model tempo.', display_averaging_s=0.12, fps=30, tasks={})
    media=a.output/'static'/'tempo'; media.mkdir(parents=True,exist_ok=True)
    for task,date,condition,stamp,camera,col in specs:
        stem=a.asset_dir/'pc2_logs'/date/condition/f'v3_{date}_{stamp}'
        meta=json.loads(Path(str(stem)+'_episode.json').read_text())
        assert int(meta['tempo']) == col
        t,r,tau,_=tempo_clock(str(stem),col=col)
        lag=json.loads((a.asset_dir/camera).read_text())['lag_s']
        done=completion(str(stem),task)
        fixed=float(np.interp(done,t,tau))
        # v18 video time starts at clip time 0; policy time = video time + lag.
        times=np.arange(0,max(done,fixed)-lag+2+1/30,1/30)
        rates=[]
        for T in times:
            window=T+lag+np.linspace(-.12,.12,25)
            rate=float(np.mean(np.interp(window,t,r,left=1,right=1)))
            rates.append([round(float(T),6),round(rate,6)])
        source=a.asset_dir/f'{task}_{stamp}_zilean_v18B_split_panel.mp4'
        target=media/f'{task}_split.mp4'
        shutil.copyfile(source,target)
        digest=hashlib.sha256(target.read_bytes()).hexdigest()
        result['tasks'][task]=dict(video=f'static/tempo/{task}_split.mp4',quantile=[90,95,99][col],lag_s=lag,policy_start_s=float(t[0]),completion_s=done,fixed_completion_s=fixed,source_rollout=f'v3_{date}_{stamp}',source_video=source.name,video_sha256=digest,samples=rates)
        print(task, 'completion',round(done,3),'fixed',round(fixed,3),'rate range',min(x[1] for x in rates),max(x[1] for x in rates),flush=True)
    result['gauge_max']=max(2,math.ceil(max(row[1] for task in result['tasks'].values() for row in task['samples'])))
    out=a.output/'static'/'data'/'tempo.json'; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,separators=(',',':'))+'\n')

if __name__=='__main__':
    main()
