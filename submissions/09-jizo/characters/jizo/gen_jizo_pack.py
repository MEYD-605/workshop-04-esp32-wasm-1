#!/usr/bin/env python3
# Jizo desk-pet — 7 animated states, 96x100, ORIGINAL ART (MIT), drawn with Pillow primitives.
# Character: a little stone Jizo / moai-monk 🗿 — grey carved stone, red bib, faint halo.
import math, os
from PIL import Image, ImageDraw
W,H = 96,100
STONE=(150,142,131); STONE_D=(112,104,94); STONE_L=(178,170,158)
OUT=(60,54,48); RED=(192,57,43); RED_D=(146,43,33); HALO=(214,178,92)
BG=(34,30,27)  # earthy dark (no solid white — house rule)
def base(draw, bob=0):
    y=bob
    # faint halo
    draw.ellipse([30,6+y,66,20+y], outline=HALO, width=1)
    # head (rounded stone)
    draw.rounded_rectangle([20,14+y,76,86+y], radius=22, fill=STONE, outline=OUT, width=3)
    # stone shading
    draw.line([26,30+y,26,72+y], fill=STONE_L, width=2)
    draw.line([70,30+y,70,72+y], fill=STONE_D, width=2)
    # red bib
    draw.rounded_rectangle([30,80+y,66,96+y], radius=6, fill=RED, outline=RED_D, width=2)
    draw.line([48,80+y,48,94+y], fill=RED_D, width=1)
def eyes(draw,kind,bob=0,t=0):
    y=bob
    lx,rx,ey=36,60,46+y
    if kind=="open":
        for x in (lx,rx): draw.ellipse([x-4,ey-5,x+4,ey+5], fill=OUT)
    elif kind=="calm":
        for x in (lx,rx): draw.arc([x-5,ey-3,x+5,ey+6],200,340,fill=OUT,width=3)
    elif kind=="closed":
        for x in (lx,rx): draw.line([x-5,ey,x+5,ey],fill=OUT,width=3)
    elif kind=="wide":
        for x in (lx,rx):
            draw.ellipse([x-5,ey-6,x+5,ey+6], fill=(245,245,240), outline=OUT)
            draw.ellipse([x-2,ey-2,x+2,ey+3], fill=OUT)
    elif kind=="happy":
        for x in (lx,rx): draw.arc([x-5,ey-4,x+5,ey+5],200,340,fill=OUT,width=3)
    elif kind=="dizzy":
        for x in (lx,rx):
            for a in range(0,360,40):
                rr=4*(a/360)+1; px=x+rr*math.cos(math.radians(a+t*40)); py=ey+rr*math.sin(math.radians(a+t*40))
                draw.point([px,py],fill=OUT)
def mouth(draw,kind,bob=0):
    y=bob; mx,my=48,66+y
    if kind=="smile": draw.arc([mx-8,my-6,mx+8,my+6],20,160,fill=OUT,width=2)
    elif kind=="o": draw.ellipse([mx-4,my-3,mx+4,my+5],outline=OUT,width=2)
    elif kind=="flat": draw.line([mx-6,my,mx+6,my],fill=OUT,width=2)
    elif kind=="grin": draw.chord([mx-9,my-7,mx+9,my+7],10,170,fill=RED_D)

def frame(state,t):
    img=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(img)
    bob=int(2*math.sin(t*math.pi))   # gentle breathing bob
    if state=="idle":
        base(d,bob); eyes(d,"calm",bob); mouth(d,"smile",bob)
    elif state=="busy":
        base(d,bob); eyes(d,"open",bob); mouth(d,"flat",bob)
        # spinning gear top-right
        cx,cy=72,22; 
        for a in range(0,360,45):
            x=cx+6*math.cos(math.radians(a+t*60)); y=cy+6*math.sin(math.radians(a+t*60))
            d.line([cx,cy,x,y],fill=HALO,width=2)
        d.ellipse([cx-3,cy-3,cx+3,cy+3],fill=STONE_D,outline=OUT)
    elif state=="attention":
        base(d,bob); eyes(d,"wide",bob); mouth(d,"o",bob)
        if t<0.5: d.line([84,16,84,30],fill=RED,width=3); d.ellipse([82,33,86,37],fill=RED)
    elif state=="celebrate":
        base(d,bob); eyes(d,"happy",bob); mouth(d,"grin",bob)
        for i,(sx,sy) in enumerate([(16,20),(80,24),(20,70),(78,66)]):
            if (i+int(t*4))%2==0:
                d.line([sx-3,sy,sx+3,sy],fill=HALO,width=1); d.line([sx,sy-3,sx,sy+3],fill=HALO,width=1)
    elif state=="dizzy":
        wob=int(3*math.sin(t*2*math.pi)); base(d,0); 
        d2=ImageDraw.Draw(img)
        eyes(d,"dizzy",0,t); mouth(d,"flat",0)
        for k in range(3):
            ang=t*2*math.pi+k*2.1; x=48+22*math.cos(ang); y=20+4*math.sin(ang)
            d.text((x,y),"*",fill=HALO)
    elif state=="sleep":
        base(d,bob); eyes(d,"closed",bob); mouth(d,"flat",bob)
        zz=["z","Z","Z"]; 
        for k in range(3):
            if k<=int(t*3): d.text((68+k*6,30-k*8),zz[k],fill=STONE_L)
    elif state=="heart":
        base(d,bob); eyes(d,"happy",bob); mouth(d,"smile",bob)
        # blush
        d.ellipse([28,58+bob,36,64+bob],fill=(200,120,110)); d.ellipse([60,58+bob,68,64+bob],fill=(200,120,110))
        hy=int(18-6*t)
        for ox in (0,):
            d.pieslice([42,hy,49,hy+7],180,360,fill=RED); d.pieslice([47,hy,54,hy+7],180,360,fill=RED)
            d.polygon([(42,hy+4),(48,hy+11),(54,hy+4)],fill=RED)
    return img

STATES=["idle","busy","attention","celebrate","dizzy","sleep","heart"]
NF=6
for s in STATES:
    frames=[frame(s,i/NF).convert("P",palette=Image.ADAPTIVE,colors=32) for i in range(NF)]
    frames[0].save(f"{s}.gif",save_all=True,append_images=frames[1:],duration=160,loop=0,disposal=2)
    print(f"  {s}.gif {os.path.getsize(s+'.gif')}B")
print("done 7 gifs")
