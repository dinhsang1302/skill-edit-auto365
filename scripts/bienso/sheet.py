"""Contact sheet 8 khung/clip để tìm biển: python sheet.py <n> ... → s_<n>.jpg"""
import cv2, sys, numpy as np, pathlib
P=pathlib.Path("../..")
for n in sys.argv[1:]:
    f=P/"insert"/f"C{n}.MP4"
    if not f.exists(): f=P/"input"/f"C{n}.MP4"
    c=cv2.VideoCapture(str(f)); N=int(c.get(7)); fps=c.get(5); tiles=[]
    for i in range(8):
        k=int((i+0.5)*N/8); c.set(1,k); ok,fr=c.read()
        fr=cv2.resize(fr,(640,360)) if ok else np.zeros((360,640,3),np.uint8)
        cv2.putText(fr,f"C{n} {k/fps:.1f}s",(8,30),0,0.9,(0,255,255),2); tiles.append(fr)
    g=np.vstack([np.hstack(tiles[:4]),np.hstack(tiles[4:])]); cv2.imwrite(f"s_{n}.jpg",g,[1,80])
