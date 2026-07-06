#!/usr/bin/env python3
# Weizen Oracle 🍺 — desk-pet character pack (jc3248-pet format).
# 96x100 GIF89a, <=16 frames, the 7 canonical states: sleep/idle/busy/attention/celebrate/dizzy/heart.
# Same GIFs decoded by gif-wasm (browser) AND AnimatedGIF (device) — many bodies, one soul.
# 100% original art (a weissbier glass), hand-drawn here -> MIT. Drawn at 48x50, 2x NEAREST -> 96x100.
import os, math
from PIL import Image, ImageDraw

W, H, S = 48, 50, 2
OUT = os.environ.get("OUT", os.path.dirname(os.path.abspath(__file__)))
os.makedirs(OUT, exist_ok=True)

BG     = (21, 17, 11)      # #15110B  (== manifest bg)
GLASS  = (90, 78, 54)
GLINT  = (236, 220, 170)
GOLD   = (245, 197, 66)    # #F5C542
AMBER  = (210, 150, 44)
CLOUD  = (250, 215, 125)
FOAM   = (246, 239, 203)   # #F6EFCB
FOAM_HI= (255, 251, 236)
EYE    = (38, 26, 10)
MOUTH  = (60, 40, 14)
SPARK  = (255, 244, 180)
THINK  = (236, 220, 170)
HEART  = (230, 70, 70)
DIM    = (150, 124, 74)

KNOTS = [(11,15,33),(14,14,34),(19,13,35),(25,14,34),(31,15,33),(37,16,32),(43,18,30),(44,18,30)]
def bounds(y):
    if y <= KNOTS[0][0]: return KNOTS[0][1], KNOTS[0][2]
    if y >= KNOTS[-1][0]: return KNOTS[-1][1], KNOTS[-1][2]
    for i in range(len(KNOTS)-1):
        y0,l0,r0 = KNOTS[i]; y1,l1,r1 = KNOTS[i+1]
        if y0 <= y <= y1:
            t = (y-y0)/(y1-y0) if y1>y0 else 0
            return l0+(l1-l0)*t, r0+(r1-r0)*t
    return KNOTS[-1][1], KNOTS[-1][2]
def lerp(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))

BEER_TOP, BEER_BOT = 13, 43

def draw_base(d, bubbles, foam_wob, beer_top=BEER_TOP, dim=1.0):
    def D(c): return tuple(int(v*dim) for v in c)
    for y in range(11, 45):
        xl, xr = bounds(y); d.line([(xl, y),(xr, y)], fill=D(GLASS))
    d.rectangle([22, 44, 26, 46], fill=D(GLASS))
    d.line([(17,47),(31,47)], fill=D(GLASS)); d.line([(18,48),(30,48)], fill=D(GLASS))
    for y in range(beer_top, BEER_BOT+1):
        xl, xr = bounds(y); f = (y-beer_top)/max(1,(BEER_BOT-beer_top))
        d.line([(int(xl)+1, y),(int(xr)-1, y)], fill=D(lerp(GOLD, AMBER, f)))
    for (cx, cy) in [(19,18),(27,22),(22,30),(29,34),(17,26),(30,28),(23,38)]:
        if cy > beer_top: d.point((cx, cy), fill=D(CLOUD))
    for (bx, by) in bubbles:
        if beer_top+1 < by < BEER_BOT:
            xl, xr = bounds(by)
            if xl+1 < bx < xr-1:
                d.point((bx, by), fill=D(CLOUD)); d.point((bx, by-1), fill=D(FOAM_HI))
    rl, rr = bounds(11)
    for x in range(int(rl)-1, int(rr)+2):
        bump = 1 if (x + foam_wob) % 4 < 2 else 0
        top = (beer_top-9) + bump + (1 if x in (int(rl)-1, int(rr)+1) else 0)
        for y in range(top, beer_top-1):
            d.point((x, y), fill=D(FOAM if (x+y) % 5 else FOAM_HI))
    d.line([(int(rl), beer_top-1),(int(rr), beer_top-1)], fill=D(FOAM_HI))
    for y in range(15, 41, 2):
        xl, _ = bounds(y); d.point((int(xl)+1, y), fill=D(GLINT))

def eyes(d, mode, ph=0.0):
    lx, rx, ey = 20, 28, 25
    if mode == "blink" or mode == "closed":
        for cx in (lx, rx): d.line([(cx-1,ey+1),(cx+1,ey+1)], fill=EYE)
        if mode == "closed": d.line([(22,30),(26,30)], fill=MOUTH)
        return
    if mode == "happy":
        for cx in (lx, rx):
            d.point((cx-1,ey+1),fill=EYE); d.point((cx,ey),fill=EYE); d.point((cx+1,ey+1),fill=EYE)
        d.line([(22,30),(26,30)], fill=MOUTH); return
    if mode == "wide":
        for cx in (lx, rx):
            d.rectangle([cx-1, ey-2, cx+1, ey+2], fill=EYE); d.point((cx, ey-1), fill=FOAM_HI)
        d.ellipse([22,29,26,32], outline=MOUTH); return
    if mode == "dizzy":
        for cx in (lx, rx):
            d.ellipse([cx-1, ey-1, cx+1, ey+1], outline=EYE)
            a = ph*2*math.pi; d.point((cx+round(math.cos(a)), ey+round(math.sin(a))), fill=EYE)
        d.line([(22,31),(23,30)], fill=MOUTH); d.line([(24,31),(25,30)], fill=MOUTH); return
    # open
    for cx in (lx, rx):
        d.rectangle([cx-1, ey-1, cx+1, ey+1], fill=EYE); d.point((cx, ey-1), fill=FOAM_HI)
    d.line([(22,30),(26,30)], fill=MOUTH); d.point((21,29),fill=MOUTH); d.point((27,29),fill=MOUTH)

def heart_at(d, x, y, col=HEART):
    d.point((x-1,y),fill=col); d.point((x+1,y),fill=col)
    d.point((x-1,y-1),fill=col); d.point((x+1,y-1),fill=col)
    d.point((x,y+1),fill=col); d.point((x-1,y+1),fill=col); d.point((x+1,y+1),fill=col)
    d.point((x,y+2),fill=col)

def zee(d, x, y, col=THINK):
    d.line([(x,y),(x+2,y)], fill=col); d.line([(x+2,y),(x,y+2)], fill=col); d.line([(x,y+2),(x+2,y+2)], fill=col)

def frame(state, i, n):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    if state == "idle":
        bub = [((19+k*7)%14+17, BEER_BOT-int((i*1.1+k*9)%28)) for k in range(3)]
        draw_base(d, bub, i); eyes(d, "blink" if i in (n-2,n-1) else "open")
    elif state == "busy":
        bub = [(((k*5+i*2)%16)+16, BEER_BOT-int((i*2.4+k*5)%30)) for k in range(6)]
        draw_base(d, bub, i*2); eyes(d, "open")
        for k in range(2):
            x = 19+k*9+(1 if i%2 else 0); d.point((x,3-(i%3)),fill=FOAM_HI); d.point((x,1),fill=FOAM)
    elif state == "attention":
        bub = [((20+k*6), BEER_BOT-int((i*1.4+k*8)%28)) for k in range(3)]
        draw_base(d, bub, i); eyes(d, "wide")
        if i % 6 < 4:                          # blinking "!" above the foam
            d.line([(24,2),(24,5)], fill=GOLD); d.point((24,7), fill=GOLD)
    elif state == "celebrate":
        bub = [((18+k*6), BEER_BOT-int((i*1.6+k*8)%28)) for k in range(4)]
        bounce = -1 if (i//2)%2==0 else 0
        base = Image.new("RGB",(W,H),BG); bd=ImageDraw.Draw(base)
        draw_base(bd, bub, i); eyes(bd, "happy"); img.paste(base,(0,bounce)); d=ImageDraw.Draw(img)
        for (sx,sy,on) in [(12,10,i%2==0),(36,9,i%2==1),(14,22,i%3==0),(35,24,i%3==1)]:
            if on:
                for dx,dy in [(0,0),(-1,0),(1,0),(0,-1),(0,1)]: d.point((sx+dx,sy+dy),fill=SPARK)
    elif state == "dizzy":
        wob = -1 if (i//3)%2==0 else 1
        bub = [((20+k*6), BEER_BOT-int((i*0.7+k*11)%28)) for k in range(2)]
        base = Image.new("RGB",(W,H),BG); bd=ImageDraw.Draw(base)
        draw_base(bd, bub, i//2); eyes(bd, "dizzy", ph=i/n); img.paste(base,(wob,0)); d=ImageDraw.Draw(img)
        for s in range(3):
            a = (i/n*2*math.pi)+s*2.1; d.point((24+round(5*math.cos(a)), 6+round(2*math.sin(a))), fill=THINK)
    elif state == "sleep":
        bub = [((22+k*4), BEER_BOT-int((i*0.4+k*13)%26)) for k in range(2)]
        draw_base(d, bub, i//3, beer_top=BEER_TOP+1, dim=0.82); eyes(d, "closed")
        for s in range(3):                      # z z z drifting up-right
            yy = 8 - s*3 - (i//2 % 3); xx = 31 + s*3
            if yy > -2: zee(d, xx, yy, col=lerp(DIM, THINK, s/2))
    elif state == "heart":
        bub = [((18+k*7), BEER_BOT-int((i*1.2+k*9)%28)) for k in range(3)]
        draw_base(d, bub, i); eyes(d, "happy")
        for s,(hx,base_y) in enumerate([(14,30),(34,32),(24,28)]):
            yy = base_y - (i*1 + s*7) % 26
            if yy > 2: heart_at(d, hx, yy, col=lerp(BG, HEART, min(1.0,(base_y-yy)/8+0.3)))
    return img.resize((W*S, H*S), Image.NEAREST)

STATES = {"idle":14,"busy":12,"attention":12,"celebrate":14,"dizzy":14,"sleep":12,"heart":14}
DUR    = {"idle":110,"busy":70,"attention":90,"celebrate":90,"dizzy":110,"sleep":190,"heart":110}
saved = {}
for st,n in STATES.items():
    frames = [frame(st,i,n) for i in range(n)]
    p = f"{OUT}/{st}.gif"
    frames[0].save(p, save_all=True, append_images=frames[1:], loop=0, duration=DUR[st],
                   disposal=2, optimize=True)
    saved[st] = frames[0]; print("wrote", p, n, "frames", os.path.getsize(p), "B")

if os.environ.get("MONTAGE"):   # dev aid: a contact sheet of all 7 states
    cols = list(STATES)
    m = Image.new("RGB",(W*S*len(cols)+10*(len(cols)+1), H*S+30),(12,10,7)); md=ImageDraw.Draw(m)
    for j,st in enumerate(cols):
        x=10+j*(W*S+10); m.paste(saved[st],(x,10)); md.text((x,H*S+14), st, fill=(200,180,120))
    out = os.path.join(OUT, "_montage.png"); m.save(out); print("montage", out)
