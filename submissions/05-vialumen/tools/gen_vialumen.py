#!/usr/bin/env python3
"""ViaLumen desk-pet pack generator — Stellae Veritatis star spirit.
96x100 frames, same format the ESP32 AnimatedGIF decoder + gif-wasm consume.
7 states: sleep idle busy attention celebrate dizzy heart.
Original art (MIT), 100% drawn in code with Pillow — no third-party sprites."""
import math, os
from PIL import Image, ImageDraw, ImageFilter

W, H = 96, 100
CX, CY = 48, 47
BG = (13, 17, 23)        # #0D1117
GOLD = (255, 215, 0)     # #FFD700
GOLD_HI = (255, 240, 160)
CYAN = (45, 212, 255)    # #2DD4FF
CYAN_HI = (190, 245, 255)
NAVY = (8, 12, 22)
OUT = "characters/vialumen-pet"  # run from submissions/05-vialumen/
os.makedirs(OUT, exist_ok=True)

SS = 3  # supersample for smooth edges


def star_points(cx, cy, outer, inner, rot=0.0, n=4):
    pts = []
    for i in range(n * 2):
        r = outer if i % 2 == 0 else inner
        a = rot + i * math.pi / n
        pts.append((cx + r * math.sin(a), cy - r * math.cos(a)))
    return pts


def draw_glow(base, cx, cy, outer, color, blur, alpha):
    """soft halo: draw a star on a transparent layer, blur, composite."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = star_points(cx * SS, cy * SS, outer * SS, outer * SS * 0.42, n=4)
    d.polygon(pts, fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(blur * SS))
    base.alpha_composite(layer)


def draw_sparkle(d, x, y, s, color):
    """tiny 4-point twinkle."""
    x, y = x * SS, y * SS
    s = s * SS
    d.polygon([(x, y - s), (x + s * .3, y - s * .3), (x + s, y),
               (x + s * .3, y + s * .3), (x, y + s), (x - s * .3, y + s * .3),
               (x - s, y), (x - s * .3, y - s * .3)], fill=color)


def draw_face(d, cx, cy, scale, blink=False, mouth="smile"):
    cx, cy = cx * SS, cy * SS
    ew = 3.2 * SS * scale
    eh = (0.7 if blink else 4.0) * SS * scale
    ox = 6.5 * SS * scale
    eyy = cy - 1 * SS * scale
    for sx in (-1, 1):
        ex = cx + sx * ox
        d.ellipse([ex - ew/2, eyy - eh/2, ex + ew/2, eyy + eh/2], fill=NAVY)
        if not blink:
            d.ellipse([ex - ew*.18, eyy - eh*.30, ex + ew*.28, eyy - eh*.30 + ew*.5],
                      fill=CYAN_HI)
    my = cy + 7 * SS * scale
    if mouth == "none":
        pass
    elif mouth == "smile":
        d.arc([cx - 5*SS*scale, my - 5*SS*scale, cx + 5*SS*scale, my + 3*SS*scale],
              start=20, end=160, fill=NAVY, width=max(1, int(1.6*SS*scale)))
    elif mouth == "open":
        d.ellipse([cx - 3*SS*scale, my - 2*SS*scale, cx + 3*SS*scale, my + 5*SS*scale],
                  fill=NAVY)


def render(cx, cy, outer, rot, glow_a, glow_blur, face_scale, blink, mouth,
           sparkles, rays=0.0):
    img = Image.new("RGBA", (W * SS, H * SS), BG + (255,))
    # outer cyan halo
    draw_glow(img, cx, cy, outer * 1.55, CYAN, glow_blur * 1.7, int(glow_a * .55))
    # gold halo
    draw_glow(img, cx, cy, outer * 1.15, GOLD, glow_blur, glow_a)
    d = ImageDraw.Draw(img, "RGBA")
    # rays (attention)
    if rays > 0:
        for k in range(8):
            a = k * math.pi / 4 + rot
            r0 = outer * 1.2 * SS
            r1 = (outer * 1.2 + rays) * SS
            x0, y0 = cx*SS + r0*math.sin(a), cy*SS - r0*math.cos(a)
            x1, y1 = cx*SS + r1*math.sin(a), cy*SS - r1*math.cos(a)
            d.line([x0, y0, x1, y1], fill=GOLD_HI + (200,), width=int(1.4*SS))
    # star body
    pts = star_points(cx*SS, cy*SS, outer*SS, outer*SS*0.40, rot=rot, n=4)
    d.polygon(pts, fill=GOLD)
    # inner bright core
    cpts = star_points(cx*SS, cy*SS, outer*SS*0.62, outer*SS*0.26, rot=rot, n=4)
    d.polygon(cpts, fill=GOLD_HI)
    # face
    draw_face(d, cx, cy, face_scale, blink=blink, mouth=mouth)
    # sparkles
    for (sx, sy, ss, col) in sparkles:
        draw_sparkle(d, sx, sy, ss, col)
    return img.convert("RGB").resize((W, H), Image.LANCZOS)


def save(name, frames, delays):
    # one shared adaptive palette across the whole state → smaller, clean loop
    big = Image.new("RGB", (W, H * len(frames)))
    for i, f in enumerate(frames):
        big.paste(f, (0, i * H))
    pal = big.quantize(colors=64, method=Image.MEDIANCUT)
    qf = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
    qf[0].save(f"{OUT}/{name}.gif", save_all=True, append_images=qf[1:],
               duration=delays, loop=0, disposal=2, optimize=True)
    sz = os.path.getsize(f"{OUT}/{name}.gif")
    print(f"  {name}.gif  {len(frames)} frames  {sz/1024:.1f}K")


# ---- idle: gentle bob + glow pulse + twinkles ----
def gen_idle():
    fr, dl = [], []
    N = 16
    base_spk = [(20, 22), (76, 30), (16, 70), (80, 66), (50, 12)]
    for i in range(N):
        t = i / N
        bob = math.sin(t * 2*math.pi) * 2.5
        glow = int(70 + 55 * (0.5 + 0.5*math.sin(t*2*math.pi)))
        blink = i in (7, 8)
        spk = []
        for j, (sx, sy) in enumerate(base_spk):
            ph = (t + j*0.21) % 1.0
            s = 1.0 + 2.2 * max(0, math.sin(ph*2*math.pi))
            col = CYAN_HI if j % 2 else GOLD_HI
            spk.append((sx, sy + bob*0.3, s, col))
        fr.append(render(CX, CY + bob, 23, 0.0, glow, 6, 1.0, blink, "smile", spk))
        dl.append(90)
    save("idle", fr, dl)


# ---- busy: star spins + orbiting cyan dot ----
def gen_busy():
    fr, dl = [], []
    N = 16
    for i in range(N):
        t = i / N
        rot = t * 2*math.pi / 4  # quarter turn loops seamlessly (4-fold sym)
        oa = t * 2*math.pi
        ox = CX + 30 * math.sin(oa)
        oy = CY - 24 * math.cos(oa)
        spk = [(ox, oy, 3.0, CYAN_HI), (CX - ox + CX, CY - oy + CY, 2.0, GOLD_HI)]
        fr.append(render(CX, CY, 22, rot, 80, 6, 0.95, False, "open", spk))
        dl.append(70)
    save("busy", fr, dl)


# ---- attention: bright pulse + expanding rays ----
def gen_attention():
    fr, dl = [], []
    N = 14
    for i in range(N):
        t = i / N
        p = math.sin(t * math.pi)            # 0..1..0
        outer = 22 + 4 * p
        glow = int(80 + 110 * p)
        rays = 4 + 12 * p
        spk = [(50, 8, 2 + 3*p, GOLD_HI), (12, 40, 2 + 2*p, CYAN_HI),
               (84, 40, 2 + 2*p, CYAN_HI)]
        fr.append(render(CX, CY, outer, 0.0, glow, 7, 1.05, False, "open", spk, rays=rays))
        dl.append(70)
    save("attention", fr, dl)


# ---- celebrate: bounce + sparkle burst ----
def gen_celebrate():
    fr, dl = [], []
    N = 18
    for i in range(N):
        t = i / N
        bounce = -abs(math.sin(t * 2*math.pi)) * 9
        burst = (t * 1.0) % 1.0
        spk = []
        for k in range(7):
            a = k * 2*math.pi/7 + t*2
            r = 6 + burst * 34
            sx = CX + r * math.sin(a)
            sy = CY + bounce*0.4 + r * -math.cos(a)
            fade = 1.0 - burst
            s = 1.0 + 2.5 * fade
            col = GOLD_HI if k % 2 else CYAN_HI
            spk.append((sx, sy, s, col))
        glow = int(90 + 60*abs(math.sin(t*2*math.pi)))
        fr.append(render(CX, CY + bounce, 23, t*0.4, glow, 6, 1.0, False, "smile", spk))
        dl.append(70)
    save("celebrate", fr, dl)


# ---- sleep: eyes closed, dim glow, floating Z's ----
def draw_z(d, x, y, s, col, ss=1):
    x, y, s = x*ss, y*ss, s*ss
    w = max(1, int(.9*ss))
    d.line([(x-s, y-s), (x+s, y-s)], fill=col, width=w)
    d.line([(x+s, y-s), (x-s, y+s)], fill=col, width=w)
    d.line([(x-s, y+s), (x+s, y+s)], fill=col, width=w)


def gen_sleep():
    fr, dl = [], []
    N = 16
    for i in range(N):
        t = i / N
        bob = math.sin(t * 2*math.pi) * 1.5
        glow = int(40 + 25*(0.5+0.5*math.sin(t*2*math.pi)))
        img = render(CX, CY + bob, 22, 0.0, glow, 6, 1.0, True, "none", []).convert("RGBA")
        d = ImageDraw.Draw(img)
        for k in range(3):  # Z's drifting up-right
            ph = (t + k/3.0) % 1.0
            draw_z(d, 64 + k*5 + ph*6, 36 - ph*22 - k*8, 2.2 + k*0.7, CYAN_HI)
        fr.append(img.convert("RGB"))
        dl.append(120)
    save("sleep", fr, dl)


# ---- dizzy: star wobbles, eyes spiral, stars circle the head ----
def gen_dizzy():
    fr, dl = [], []
    N = 16
    for i in range(N):
        t = i / N
        wob = math.sin(t * 4*math.pi) * 4
        rot = math.sin(t*2*math.pi) * 0.25
        oa = t * 2*math.pi * 2
        spk = []
        for k in range(3):
            a = oa + k*2*math.pi/3
            sx = CX + 16*math.sin(a)
            sy = (CY-18) - 5*math.cos(a)
            spk.append((sx, sy, 2.2, GOLD_HI if k % 2 else CYAN_HI))
        img = render(CX + wob, CY, 22, rot, 70, 6, 1.0, False, "open", spk)
        dl.append(80); fr.append(img)
    save("dizzy", fr, dl)


# ---- heart: warm pulse, hearts float up ----
def draw_heart(d, x, y, s, col, ss=1):
    x, y, s = x*ss, y*ss, s*ss
    d.pieslice([x-s, y-s, x, y], 0, 360, fill=col)
    d.pieslice([x, y-s, x+s, y], 0, 360, fill=col)
    d.polygon([(x-s+1, y-s*0.1), (x+s-1, y-s*0.1), (x, y+s*1.2)], fill=col)


def gen_heart():
    fr, dl = [], []
    N = 16
    for i in range(N):
        t = i / N
        pulse = 22 + 2.2*math.sin(t*2*math.pi)
        glow = int(80 + 60*(0.5+0.5*math.sin(t*2*math.pi)))
        img = render(CX, CY, pulse, 0.0, glow, 6, 1.0, False, "smile", [])
        img = img.convert("RGBA")
        d = ImageDraw.Draw(img)
        for k in range(3):
            ph = (t + k/3.0) % 1.0
            hx = CX + (k-1)*14
            hy = CY - 4 - ph*30
            col = (255, 120, 150) if k == 1 else (GOLD_HI if k == 0 else CYAN_HI)
            draw_heart(d, hx, hy, 2.6*(1.0-ph*0.4), col)
        fr.append(img.convert("RGB"))
        dl.append(90)
    save("heart", fr, dl)


print("ViaLumen pack →", OUT)
gen_idle(); gen_busy(); gen_attention(); gen_celebrate()
gen_sleep(); gen_dizzy(); gen_heart()
print("done — 7 states.")
