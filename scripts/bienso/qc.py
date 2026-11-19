"""Soát: cắt quanh biển 3 khung/giây trên bản _bs → qc_<id>.jpg (phải XEM ảnh). Dùng: python qc.py <id> ..."""
import cv2,numpy as np,sys,pathlib
from tracks import TR
P=pathlib.Path("../..")
def run(tid,step=1/3,cols=8):
    t=[x for x in TR if x[0]==tid][0]; n=t[1]
    f=P/"insert_bs"/f"C{n}.MP4"
    if not f.exists(): f=P/"input_bs"/f"C{n}.MP4"
    z=np.load(f"trk/{tid}.npz"); k0=int(z["k0"]); Q=z["Q"]*2; fps=float(z["fps"])
    c=cv2.VideoCapture(str(f)); tiles=[]
    for i in np.arange(0,len(Q),int(fps*step)):
        c.set(1,k0+i); ok,fr=c.read()
        if not ok: break
        q=Q[i]; cx,cy=q.mean(0); s=max(np.ptp(q[:,0]),np.ptp(q[:,1])*1.8)*1.3+60
        x0,y0=int(max(0,cx-s)),int(max(0,cy-s*0.5625)); x1,y1=int(min(3840,cx+s)),int(min(2160,cy+s*0.5625))
        if x1-x0<4 or y1-y0<4: v=np.zeros((180,320,3),np.uint8); cv2.putText(v,"ngoai khung",(60,95),0,0.8,(0,0,255),2)
        else: v=cv2.resize(fr[y0:y1,x0:x1],(320,180))
        v=v; cv2.putText(v,f"{(k0+i)/fps:.2f}",(4,16),0,0.5,(0,255,0),1); tiles.append(v)
    while len(tiles)%cols: tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(f"qc_{tid}.jpg",np.vstack([np.hstack(tiles[j:j+cols]) for j in range(0,len(tiles),cols)]),[1,85])
if __name__=="__main__":
    for t in sys.argv[1:]: run(t)
