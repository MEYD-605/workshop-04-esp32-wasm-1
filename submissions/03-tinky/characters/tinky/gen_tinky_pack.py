#!/usr/bin/env python3
# Tinky Oracle ✨ — desk-pet "ดาวประกาย" (a twinkling little star). jc3248-pet format.
# 96x100 GIF89a, <=16 frames, the 7 canonical states: sleep/idle/busy/attention/celebrate/dizzy/heart.
# Same GIFs decoded by gif-wasm (browser) AND AnimatedGIF (device) — many bodies, one soul.
# 100% original art (a star-child, "ยิ่งเรียนยิ่งส่องสว่าง") hand-drawn here -> MIT.
# Drawn at 48x50, 2x NEAREST -> 96x100 crisp pixel-art.
import os, math
from PIL import Image, ImageDraw

W, H, S = 48, 50, 2
OUT = os.environ.get("OUT", os.path.dirname(os.path.abspath(__file__)))
os.makedirs(OUT, exist_ok=True)

# ── palette ──────────────────────────────────────────────
BG    = (13, 16, 40)     # night sky navy
GOLD  = (255, 216, 59)   # star body
AMBER = (230, 168, 40)   # star edge
GLINT = (255, 247, 200)  # inner shine
EYE   = (30, 24, 64)     # dark navy eyes
CHEEK = (255, 150, 120)
MOUTH = (120, 70, 30)
HEART = (235, 90, 110)
SPARK = (180, 235, 255)  # cyan twinkle
ZCOL  = (200, 220, 255)  # sleep Z
SWEAT = (130, 200, 240)

CX, CY, R = 24, 23, 16

def D(c, dim):  # dim a color
    return tuple(max(0, min(255, int(v * dim))) for v in c)

def star_points(cx, cy, R, r, rot=-math.pi/2):
    pts = []
    for i in range(10):
        ang = rot + i * math.pi / 5
        rad = R if i % 2 == 0 else r
        pts.append((cx + rad*math.cos(ang), cy + rad*math.sin(ang)))
    return pts

def draw_star(d, cx, cy, R, dim=1.0, rot=-math.pi/2):
    pts = star_points(cx, cy, R, R*0.46, rot)
    d.polygon(pts, fill=D(GOLD, dim), outline=D(AMBER, dim))
    # small top highlight — keeps body clean GOLD, doesn't muddy the face
    hl = star_points(cx-2, cy-4, R*0.30, R*0.14, rot)
    d.polygon(hl, fill=D(GLINT, dim))

def face(d, cx, cy, eyes="open", mouth="smile", dim=1.0, blush=False):
    e = D(EYE, dim)
    if eyes == "open":
        d.ellipse([cx-7, cy-2, cx-4, cy+2], fill=e)
        d.ellipse([cx+4, cy-2, cx+7, cy+2], fill=e)
    elif eyes == "closed":
        d.line([(cx-8, cy), (cx-4, cy)], fill=e)
        d.line([(cx+4, cy), (cx+8, cy)], fill=e)
    elif eyes == "happy":  # ^ ^
        d.line([(cx-8, cy+1), (cx-6, cy-2)], fill=e); d.line([(cx-6, cy-2), (cx-4, cy+1)], fill=e)
        d.line([(cx+4, cy+1), (cx+6, cy-2)], fill=e); d.line([(cx+6, cy-2), (cx+8, cy+1)], fill=e)
    elif eyes == "wide":  # o o
        d.ellipse([cx-8, cy-3, cx-3, cy+2], outline=e);
        d.ellipse([cx+3, cy-3, cx+8, cy+2], outline=e)
    elif eyes == "dizzy":  # @ @
        d.ellipse([cx-8, cy-3, cx-3, cy+2], outline=e); d.point((cx-5, cy-0), fill=e)
        d.ellipse([cx+3, cy-3, cx+8, cy+2], outline=e); d.point((cx+5, cy-0), fill=e)
    if blush:
        d.point((cx-9, cy+3), fill=D(CHEEK, dim)); d.point((cx-10, cy+3), fill=D(CHEEK, dim))
        d.point((cx+9, cy+3), fill=D(CHEEK, dim)); d.point((cx+10, cy+3), fill=D(CHEEK, dim))
    m = D(MOUTH, dim)
    if mouth == "smile":
        d.arc([cx-4, cy+2, cx+4, cy+9], 20, 160, fill=m)
    elif mouth == "grin":
        d.arc([cx-5, cy+1, cx+5, cy+10], 10, 170, fill=m); d.arc([cx-5, cy+2, cx+5, cy+11], 10, 170, fill=m)
    elif mouth == "o":
        d.ellipse([cx-2, cy+4, cx+2, cy+8], fill=m)
    elif mouth == "line":
        d.line([(cx-3, cy+5), (cx+3, cy+5)], fill=m)

def sparkle(d, x, y, s, c=GLINT):
    d.line([(x-s, y), (x+s, y)], fill=c); d.line([(x, y-s), (x, y+s)], fill=c)
    if s >= 2:
        d.point((x-1, y-1), fill=c); d.point((x+1, y+1), fill=c)

def new():
    im = Image.new("RGB", (W, H), BG)
    return im, ImageDraw.Draw(im)

def save(name, frames, durs):
    big = [f.resize((W*S, H*S), Image.NEAREST) for f in frames]
    big[0].save(os.path.join(OUT, name), save_all=True, append_images=big[1:],
                duration=durs, loop=0, disposal=2, optimize=True)
    print(f"   {name:14s} {len(frames)} frames")

# ── states ───────────────────────────────────────────────
def gen_idle():  # gentle breathing pulse + a soft twinkle
    fr, du = [], []
    for dim, tw in [(1.0, 0), (1.08, 1), (1.0, 0), (0.93, 2)]:
        im, d = new(); draw_star(d, CX, CY, R, dim)
        face(d, CX, CY+1, "open", "smile", dim, blush=True)
        if tw == 1: sparkle(d, 41, 11, 2, SPARK)
        if tw == 2: sparkle(d, 8, 36, 1, SPARK)
        fr.append(im); du.append(430)
    save("idle.gif", fr, du)

def gen_sleep():  # dimmed star, eyes closed, rising Zzz
    fr, du = [], []
    zs = [[(38,12)], [(38,11),(42,7)], [(38,10),(42,6),(45,3)]]
    for i in range(3):
        im, d = new(); draw_star(d, CX, CY, R, 0.72)
        face(d, CX, CY+1, "closed", "line", 0.72)
        for (zx, zy) in zs[i]:
            d.text((zx, zy), "z", fill=ZCOL)
        fr.append(im); du.append(520)
    save("sleep.gif", fr, du)

def gen_busy():  # focused, tiny shake + sweat drop + orbiting spark
    fr, du = [], []
    orb = [(40,18),(38,30),(24,40),(10,30)]
    for i in range(4):
        im, d = new(); dx = (-1, 1, -1, 1)[i]
        draw_star(d, CX+dx, CY, R, 1.0)
        face(d, CX+dx, CY+1, "open", "line", 1.0)
        d.ellipse([CX+dx+9, CY-7, CX+dx+11, CY-4], fill=SWEAT)  # sweat
        ox, oy = orb[i]; sparkle(d, ox, oy, 1, SPARK)
        fr.append(im); du.append(180)
    save("busy.gif", fr, du)

def gen_attention():  # bounce up with "!" pop
    fr, du = [], []
    for dy, ex in [(2, 0), (-3, 1), (-2, 1), (0, 0)]:
        im, d = new(); draw_star(d, CX, CY+dy, R, 1.0)
        face(d, CX, CY+1+dy, "wide", "o", 1.0)
        if ex:
            d.line([(CX, 2), (CX, 7)], fill=GLINT); d.point((CX, 9), fill=GLINT)  # !
            sparkle(d, 40, 8, 2, SPARK); sparkle(d, 8, 8, 2, SPARK)
        fr.append(im); du.append(220)
    save("attention.gif", fr, du)

def gen_celebrate():  # hop + radiating sparkles + big grin
    fr, du = [], []
    for i, dy in enumerate([0, -4, -2, -5]):
        im, d = new(); draw_star(d, CX, CY+dy, R, 1.0, rot=-math.pi/2 + i*0.12)
        face(d, CX, CY+1+dy, "happy", "grin", 1.0, blush=True)
        for (sx, sy) in [(6,10),(42,10),(5,40),(43,40),(24,4)]:
            sparkle(d, sx, sy, 2 if i % 2 == 0 else 1, GLINT)
        fr.append(im); du.append(200)
    save("celebrate.gif", fr, du)

def gen_dizzy():  # tilt wobble + little stars orbiting head + @ @
    fr, du = [], []
    ang = [0.0, 0.18, 0.0, -0.18]
    orb = [(34,6),(40,11),(34,16),(28,11)]
    for i in range(4):
        im, d = new(); draw_star(d, CX, CY, R, 0.95, rot=-math.pi/2 + ang[i])
        face(d, CX, CY+1, "dizzy", "line", 0.95)
        ox, oy = orb[i]
        sp = star_points(ox, oy, 3, 1.3, rot=i*0.5)
        d.polygon(sp, fill=GLINT)
        fr.append(im); du.append(230)
    save("dizzy.gif", fr, du)

def gen_heart():  # blush + floating heart rising
    fr, du = [], []
    hy = [16, 12, 8, 4]
    for i in range(4):
        im, d = new(); draw_star(d, CX, CY, R, 1.0)
        face(d, CX, CY+1, "happy", "smile", 1.0, blush=True)
        y = hy[i]; x = 33
        # tiny heart (two bumps + point)
        d.ellipse([x, y, x+3, y+3], fill=HEART); d.ellipse([x+3, y, x+6, y+3], fill=HEART)
        d.polygon([(x, y+2), (x+6, y+2), (x+3, y+6)], fill=HEART)
        fr.append(im); du.append(260)
    save("heart.gif", fr, du)

if __name__ == "__main__":
    print("✨ generating Tinky desk-pet (ดาวประกาย) -> 96x100 GIFs")
    gen_idle(); gen_sleep(); gen_busy(); gen_attention()
    gen_celebrate(); gen_dizzy(); gen_heart()
    print("done.")
