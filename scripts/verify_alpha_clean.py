# verify_alpha_clean.py
import sys, pathlib
from PIL import Image
bad=[]
for p in pathlib.Path(sys.argv[1]).rglob("*.png"):
    im=Image.open(p).convert("RGBA"); px=im.load()
    w,h=im.size
    for y in range(h):
        for x in range(w):
            r,g,b,a=px[x,y]
            if a==0 and (r or g or b):
                bad.append(p); y=h; break
print("NG files:", len(bad))
for p in bad[:20]: print(" -", p)
