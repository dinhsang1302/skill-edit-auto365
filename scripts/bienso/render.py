"""Vẽ tấm che theo vết bám trk/<id>.npz → insert_bs/ hoặc input_bs/ (cùng độ phân giải, fps, số khung, giữ audio). Dùng: python render.py <n> ..."""
import cv2, numpy as np, subprocess, sys, pathlib, time
from cand import src
from tracks import TR
from track import fps_of
import sys as _s
ENC=(["-c:v","h264_videotoolbox","-b:v","150M"] if _s.platform=="darwin" else ["-c:v","h264_nvenc","-preset","p5","-rc","vbr","-cq","16","-b:v","0","-maxrate","180M","-bufsize","360M"])
P=pathlib.Path("../.."); W,H=3840,2160   # đổi theo nguồn nếu không phải 4K 16:9
SOFT={t[0]: t[6] for t in TR if len(t) > 6}   # xe nền mất nét → tấm che mềm theo (trường thứ 7 trong tracks.py)
def plate_tex(w,h,col):
    """tấm biển trắng trơn bo góc, viền xám mảnh, ảnh BGR + alpha cỡ (h,w)"""
    s=4; W_,H_=w*s,h*s; img=np.zeros((H_,W_,3),np.float32); a=np.zeros((H_,W_),np.uint8)
    r=int(min(W_,H_)*0.10); bw=max(s,int(min(W_,H_)*0.035))
    def rr(m,x0,y0,x1,y1,r,c):
        cv2.rectangle(m,(x0+r,y0),(x1-r,y1),c,-1); cv2.rectangle(m,(x0,y0+r),(x1,y1-r),c,-1)
        for cx,cy in((x0+r,y0+r),(x1-r,y0+r),(x0+r,y1-r),(x1-r,y1-r)): cv2.circle(m,(cx,cy),r,c,-1,cv2.LINE_AA)
    rr(a,0,0,W_-1,H_-1,r,255)
    edge=np.array(col,np.float32)*0.62; rr(img,0,0,W_-1,H_-1,r,tuple(map(float,edge)))
    rr(img,bw,bw,W_-1-bw,H_-1-bw,max(1,r-bw),tuple(map(float,col)))
    g=np.linspace(1.0,0.94,H_,dtype=np.float32)[:,None,None]; img*=g      # sáng trên, tối nhẹ dưới
    img=cv2.resize(img,(w,h),interpolation=cv2.INTER_AREA); a=cv2.resize(a,(w,h),interpolation=cv2.INTER_AREA)
    return img,a.astype(np.float32)/255
def expand(q,k):
    c=q.mean(0); return c+(q-c)*k
def draw(fr,q,style,state,key):
    x0,y0=np.floor(q.min(0)).astype(int)-8; x1,y1=np.ceil(q.max(0)).astype(int)+8
    X0,Y0,X1,Y1=max(0,x0),max(0,y0),min(W,x1),min(H,y1)
    if X1<=X0 or Y1<=Y0: return
    roi=fr[Y0:Y1,X0:X1].astype(np.float32); g=cv2.cvtColor(fr[Y0:Y1,X0:X1],cv2.COLOR_BGR2GRAY)
    m=np.zeros(g.shape,np.uint8); cv2.fillConvexPoly(m,(q-[X0,Y0]).astype(np.int32),255)
    if style=="plate":
        pix=roi[(m>0)&(g>=np.percentile(g[m>0],75))] if (m>0).sum()>20 else roi.reshape(-1,3)
        col=pix.mean(0); gm=col.mean(); col=0.45*col+0.55*gm      # trắng theo ánh sáng tại chỗ, bớt ám màu
        col=np.clip(col*1.02,40,246)
    else:
        big=fr[max(0,y0-40):min(H,y1+40),max(0,x0-60):min(W,x1+60)].reshape(-1,3).astype(np.float32)
        gb=big.mean(1); col=np.median(big[gb>np.percentile(gb,60)],0)
    old=state.get(key); col=col if old is None else old*0.85+col*0.15; state[key]=col
    if style=="plate":
        tw=int(max(np.linalg.norm(q[1]-q[0]),np.linalg.norm(q[2]-q[3]))); th=int(max(np.linalg.norm(q[3]-q[0]),np.linalg.norm(q[2]-q[1])))
        tw,th=max(tw,8),max(th,6); img,al=plate_tex(tw,th,col)
        Hm=cv2.getPerspectiveTransform(np.float32([[0,0],[tw,0],[tw,th],[0,th]]),(q-[X0,Y0]).astype(np.float32))
        im=cv2.warpPerspective(img,Hm,(X1-X0,Y1-Y0),flags=cv2.INTER_LINEAR); A=cv2.warpPerspective(al,Hm,(X1-X0,Y1-Y0),flags=cv2.INTER_LINEAR)
    else:
        mk=((m>0)&(g>45)).astype(np.uint8)*255; mk=cv2.dilate(mk,np.ones((7,7),np.uint8))&((g>45).astype(np.uint8)*255)
        L=fr[Y0:Y1,max(0,X0-70):max(1,X0-6)].astype(np.float32)                      # thân xe ngay bên trái, cùng hàng
        gl=L.mean(2); rows=np.stack([np.median(L[r][gl[r]>np.percentile(gl[r],40)],0) if L.shape[1] else col for r in range(L.shape[0])])
        rows=cv2.GaussianBlur(rows[:,None,:],(1,0),sigmaX=0,sigmaY=6)[:,0,:] if len(rows)>3 else rows
        im=np.repeat(rows[:,None,:],X1-X0,1); A=cv2.GaussianBlur(mk.astype(np.float32)/255,(0,0),2.5)
    sg=SOFT.get(key,0)
    if sg: im=cv2.GaussianBlur(im,(0,0),sg); A=cv2.GaussianBlur(A,(0,0),sg)
    A=cv2.GaussianBlur(A,(0,0),1.2)[...,None]
    im=im+np.random.normal(0,2.2 if style=="plate" else 1.2,im.shape).astype(np.float32)
    fr[Y0:Y1,X0:X1]=np.clip(roi*(1-A)+im*A,0,255).astype(np.uint8)
def run(n):
    f=src(n); sub="insert_bs" if "insert" in str(f) else "input_bs"; (P/sub).mkdir(exist_ok=True)
    out=P/sub/f.name; tmp=out.with_suffix(".part.mp4")
    trs=[]
    for t in TR:
        if t[1]!=n: continue
        z=np.load(f"trk/{t[0]}.npz"); trs.append((t[0],int(z["k0"]),z["Q"]*(W/1920),str(z["style"])))
    dec=subprocess.Popen(["ffmpeg","-v","error",*(["-hwaccel","cuda"] if _s.platform=="win32" else ["-hwaccel","videotoolbox"]),"-i",str(f),"-f","rawvideo","-pix_fmt","bgr24","-"],stdout=subprocess.PIPE,bufsize=W*H*3)
    enc=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","bgr24","-s",f"{W}x{H}","-r",str(fps_of(f)),"-i","-","-i",str(f),
        "-map","0:v","-map","1:a:0",*ENC,
        "-pix_fmt","yuv420p","-c:a","copy","-shortest",str(tmp)],stdin=subprocess.PIPE)
    st={}; k=0; t0=time.time()
    while True:
        b=dec.stdout.read(W*H*3)
        if len(b)<W*H*3: break
        fr=np.frombuffer(b,np.uint8).reshape(H,W,3).copy()
        for tid,k0,Q,style in trs:
            i=k-k0
            if 0<=i<len(Q) and not np.isnan(Q[i]).any():
                draw(fr,expand(Q[i],1.08 if style=="plate" else 1.15),style,st,tid)
        enc.stdin.write(fr.tobytes()); k+=1
    enc.stdin.close(); enc.wait(); dec.wait()
    if enc.returncode: raise SystemExit(f"encode lỗi {n}")
    tmp.replace(out); print(n,"→",out,f"{k} khung {time.time()-t0:.0f}s",flush=True)
if __name__=="__main__":
    for n in sys.argv[1:]: run(n)
