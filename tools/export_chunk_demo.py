"""Export a fixed logged proposal and its three tempo channels; no controller simulation."""
import argparse
import json
from pathlib import Path
import sys

p=argparse.ArgumentParser()
p.add_argument('--analysis-dir',required=True)
p.add_argument('--chunks',required=True)
p.add_argument('--output',default='static/data/chunk.json')
a=p.parse_args()
sys.path.insert(0,a.analysis_dir)
import numpy as np
from v04_fk import fk
source=json.loads(Path(a.chunks).read_text())
q=source['queries'][0]
assert q['rtc_prefix_len']==0
actions=np.asarray(q['actions'])
xyz=fk(np.vstack([np.asarray(q['state'])[:7],actions[:,:7]]))
tempo=np.asarray(q['tempo']); assert tempo.shape==(15,3)
clocks={'q50':(np.arange(16)/15).tolist()}
for col,name in enumerate(['q90','q95','q99']):
    clocks[name]=np.r_[0,np.cumsum(1/(15*np.exp(tempo[:,col])))].tolist()
result=dict(source_rollout=Path(a.chunks).name,query=q['query'],query_t=q['t'],frame='robot-base flange, metres',xyz=xyz.tolist(),log_tempo=tempo.tolist(),clocks=clocks,baseline='q50 means nominal 1/15-second path clock; no q50 output channel is stored.',context_video='static/tempo/cup_context.mp4')
Path(a.output).write_text(json.dumps(result,separators=(',',':'))+'\n')
print({k:round(v[-1],4) for k,v in clocks.items()})
