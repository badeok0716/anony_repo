"""Cup-only short afterimage pilot. Same timing and left lane; recent right-lane finger patches only."""
import argparse
from collections import deque
import subprocess
import cv2
import imageio_ffmpeg
import numpy as np

p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args()
cap=cv2.VideoCapture(a.source);fps=cap.get(cv2.CAP_PROP_FPS);w=int(cap.get(3));h=int(cap.get(4))
out=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r',str(fps),'-i','-','-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',a.output],stdin=subprocess.PIPE)
history=deque(maxlen=4);n=0;rad=round(h*.085)
yy,xx=np.mgrid[-rad:rad,-rad:rad];mask=np.clip((1-np.hypot(xx,yy)/rad)/.8,0,1)[...,None]
while True:
    ok,frame=cap.read()
    if not ok:break
    t=n/fps;n+=1;result=frame.copy()
    small=cv2.resize(frame[:,w//2:],(128,128)).astype(float);b,g,r=cv2.split(small)
    valid=(r>100)&(r>1.55*g)&(r>1.35*b);valid[:12]=False;valid[112:]=False;valid[:,:6]=False;valid[:,122:]=False
    y,x=np.where(valid)
    if len(x)>=4:
        cx=round(w/2+x.mean()/128*w/2);cy=round(y.mean()/128*h)
        for age,ox,oy,patch in history:
            dt=t-age
            if not .035<=dt<=.17:continue
            x0,x1=max(w//2,ox-rad),min(w,ox+rad);y0,y1=max(0,oy-rad),min(h,oy+rad)
            mx,my=x0-(ox-rad),y0-(oy-rad)
            alpha=.4*(1-dt/.20)*mask[my:my+y1-y0,mx:mx+x1-x0]
            result[y0:y1,x0:x1]=(result[y0:y1,x0:x1]*(1-alpha)+patch[my:my+y1-y0,mx:mx+x1-x0]*alpha).astype(np.uint8)
        if cx-rad>=w//2 and cx+rad<=w and cy-rad>=0 and cy+rad<=h:
            history.append((t,cx,cy,frame[cy-rad:cy+rad,cx-rad:cx+rad].copy()))
    else:history.clear()
    out.stdin.write(result.tobytes())
cap.release();out.stdin.close();assert out.wait()==0
print(f'{n} frames, {n/fps:.3f}s, {w}x{h}',flush=True)
