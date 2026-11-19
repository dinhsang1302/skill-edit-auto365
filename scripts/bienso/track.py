"""Bám biển theo phối cảnh: LK flow + homography (RANSAC, kiểm thuận/ngược), từ khung mồi chạy xuôi + ngược, làm mượt 5 khung. Dùng: python track.py <id> ..."""
import cv2, numpy as np, subprocess, sys, json, pathlib
from cand import src
from tracks import TR
OUT=pathlib.Path("trk"); OUT.mkdir(exist_ok=True)
def fps_of(f):
    r=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=r_frame_rate","-of","csv=p=0",str(f)],capture_output=True,text=True).stdout.strip()
    a,b=r.split("/"); return float(a)/float(b)
def frames(f, k0, k1, fps):
    W,H=1920,1080
    cmd=["ffmpeg","-v","error",*(["-hwaccel","cuda"] if sys.platform=="win32" else ["-hwaccel","videotoolbox"]),"-i",str(f),"-vf",rf"select='between(n\,{k0}\,{k1})',scale={W}:{H}:flags=area,format=gray","-fps_mode","passthrough","-f","rawvideo","-"]
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE); out=[]
    while True:
        b=p.stdout.read(W*H)
        if len(b)<W*H: break
        out.append(np.frombuffer(b,np.uint8).reshape(H,W))
    p.wait(); return out
def step(g0,g1,q):
    x0,y0=q.min(0); x1,y1=q.max(0); s=max(x1-x0,y1-y0); pad=max(90,1.6*s)
    X0,Y0=int(max(0,x0-pad)),int(max(0,y0-pad)); X1,Y1=int(min(1920,x1+pad)),int(min(1080,y1+pad))
    m=np.zeros_like(g0); m[Y0:Y1,X0:X1]=255
    p0=cv2.goodFeaturesToTrack(g0,300,0.005,4,mask=m)
    if p0 is None or len(p0)<6: return q,0
    lk=dict(winSize=(21,21),maxLevel=3,criteria=(3,30,0.01))
    p1,st,_=cv2.calcOpticalFlowPyrLK(g0,g1,p0,None,**lk); pb,st2,_=cv2.calcOpticalFlowPyrLK(g1,g0,p1,None,**lk)
    ok=(st[:,0]==1)&(st2[:,0]==1)&(np.linalg.norm((pb-p0).reshape(-1,2),axis=1)<0.8)
    a,b=p0[ok],p1[ok]
    if len(a)<6: return q,len(a)
    if len(a)>=12:
        H,inl=cv2.findHomography(a,b,cv2.RANSAC,1.5)
        if H is not None and inl.sum()>=10:
            A=H[:2,:2]; d=np.linalg.det(A)
            if 0.85<d<1.18 and abs(H[2,0])<2e-3 and abs(H[2,1])<2e-3:
                return cv2.perspectiveTransform(q.reshape(-1,1,2),H).reshape(4,2),int(inl.sum())
    M,inl=cv2.estimateAffinePartial2D(a,b,method=cv2.RANSAC,ransacReprojThreshold=1.5)
    if M is None: return q,0
    return (q@M[:,:2].T+M[:,2]),int(inl.sum())
def run(tid):
    t=[x for x in TR if x[0]==tid][0]; _,n,ts,q,(a,b),style=t[:6]; f=src(n); fps=fps_of(f)
    k0,k1,ks=int(a*fps),int(b*fps),int(round(ts*fps)); fr=frames(f,k0,k1,fps); N=len(fr)
    Q=np.full((N,4,2),np.nan,np.float32); si=ks-k0; Q[si]=np.array(q,np.float32); weak=[]
    for i in range(si+1,N):
        Q[i],c=step(fr[i-1],fr[i],Q[i-1]); 
        if c<12: weak.append(i)
    for i in range(si-1,-1,-1):
        Q[i],c=step(fr[i+1],fr[i],Q[i+1])
        if c<12: weak.append(i)
    # smooth corners (window 5, edges kept)
    S=Q.copy(); w=2
    for i in range(N):
        lo,hi=max(0,i-w),min(N,i+w+1); S[i]=Q[lo:hi].mean(0)
    np.savez(OUT/f"{tid}.npz",k0=k0,fps=fps,Q=S,style=style)
    print(tid,n,f"{N} khung, yếu {len(weak)}",flush=True)
if __name__=="__main__":
    for tid in sys.argv[1:]: run(tid)
