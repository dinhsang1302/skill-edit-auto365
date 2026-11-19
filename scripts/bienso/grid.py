"""Khung có lưới 100 px để định vị vùng biển: python grid.py out.jpg <n>:<t> ..."""
import cv2,numpy as np,sys
from cand import src
tiles=[]
for a in sys.argv[2:]:
    n,t=a.split(":"); t=float(t)
    c=cv2.VideoCapture(str(src(n))); c.set(0,t*1000); ok,fr=c.read(); fr=cv2.resize(fr,(1920,1080))
    for x in range(100,1920,100): cv2.line(fr,(x,0),(x,1080),(0,255,255) if x%500==0 else (0,180,255),1)
    for y in range(100,1080,100): cv2.line(fr,(0,y),(1920,y),(0,255,255) if y%500==0 else (0,180,255),1)
    for x in range(100,1920,100):
        for y in range(100,1080,200): cv2.putText(fr,f"{x//100}",(x+3,y-5),0,0.8,(0,255,0),2)
    for y in range(100,1080,100): cv2.putText(fr,f"y{y//100}",(5,y-5),0,0.8,(0,255,0),2)
    cv2.putText(fr,f"C{n} {t}s",(20,1060),0,1.5,(255,0,255),4)
    tiles.append(cv2.resize(fr,(960,540),interpolation=cv2.INTER_AREA))
while len(tiles)%2: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(sys.argv[1],np.vstack([np.hstack(tiles[i:i+2]) for i in range(0,len(tiles),2)]),[1,88])
