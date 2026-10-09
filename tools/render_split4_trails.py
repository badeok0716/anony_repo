"""Two local afterimages per lane on the original v18 B split4 panel."""
import argparse
from collections import deque
import subprocess
import cv2
import imageio_ffmpeg
import numpy as np

p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args()
cap=cv2.VideoCapture(a.source);fps=cap.get(5);w=int(cap.get(3));h=int(cap.get(4))
assert w==1232 and h==482,(w,h)
pipe=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r',str(fps),'-i','-','-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',a.output],stdin=subprocess.PIPE)
history=[deque(maxlen=10) for _ in range(4)]
radius=38;yy,xx=np.mgrid[-radius:radius,-radius:radius]
feather=np.clip((1-np.hypot(xx,yy)/radius)/.35,0,1)
n=0
while True:
    ok,frame=cap.read()
    if not ok:break
    result=frame.copy()
    for lane in range(4):
        left=lane*312;region=frame[:,left:left+296]
        b,g,r=cv2.split(region.astype(float))
        red=((r>110)&(g<90)&(b<90)&(r>2*g)&(r>2*b)).astype(np.uint8)
        red[:65]=0;red[-50:]=0
        count,labels,stats,centers=cv2.connectedComponentsWithStats(red)
        if count<2:continue
        k=1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
        if stats[k,cv2.CC_STAT_AREA]<4:continue
        cx,cy=np.round(centers[k]).astype(int)
        if not(radius<=cx<296-radius and radius<=cy<h-radius):continue
        patch=region[cy-radius:cy+radius,cx-radius:cx+radius].copy()
        for fn,ox,oy,old in history[lane]:
            if n-fn not in (3,6):continue
            bb,gg,rr=cv2.split(old.astype(float))
            keep=((rr>85)&(rr>gg*1.4)&(rr>bb*1.25))|(np.maximum.reduce([bb,gg,rr])<95)
            alpha=(.30 if n-fn==3 else .18)*feather*keep
            dst=result[oy-radius:oy+radius,left+ox-radius:left+ox+radius]
            tint=old*.65+np.array([65,55,5])
            dst[:]=(dst*(1-alpha[...,None])+tint*alpha[...,None]).clip(0,255).astype(np.uint8)
        # Current fingers stay crisp; both sides receive identical effect settings.
        result[:,left:left+296][red.astype(bool)]=region[red.astype(bool)]
        history[lane].append((n,cx,cy,patch))
    pipe.stdin.write(result.tobytes());n+=1
cap.release();pipe.stdin.close();assert pipe.wait()==0
print(f'{n} frames / {n/fps:.2f}s / {w}x{h}; 2 ghosts at 0.10, 0.20s in ALL four lanes')
