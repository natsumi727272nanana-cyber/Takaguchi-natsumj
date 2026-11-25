"""1本目リール「この冬1番人気オーダー マロングレージュ」を組み立てる。
使い方: python3 video/tools/build_reel1.py  （素材は video/raw/、出力は video/output/）
"""
import math, os, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
OUT = os.path.join(ROOT, "output")
WORK = os.path.join(OUT, "work")
W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

WHITE = (255, 255, 255, 255)
INK = (52, 36, 28, 255)          # 縁取りの濃いブラウン
MARRON = (216, 178, 140, 255)    # タイトルのマロン色
GOLD = (245, 214, 140, 255)

def font(size):
    return ImageFont.truetype(FONT, size, index=0)

def canvas():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))

def text_center(img, y, s, size, fill=WHITE, stroke=INK, sw=None, shadow=True):
    d = ImageDraw.Draw(img)
    f = font(size)
    sw = sw if sw is not None else max(4, size // 9)
    w = d.textlength(s, font=f)
    x = (W - w) / 2
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((x + 4, y + 6), s, font=f, fill=(0, 0, 0, 150),
                                stroke_width=sw, stroke_fill=(0, 0, 0, 150))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
        d = ImageDraw.Draw(img)
    d.text((x, y), s, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)

def rich_center(img, y, parts, size, sw=None):
    """parts=[(文字, 色, 倍率)]を1行で中央に並べる"""
    d = ImageDraw.Draw(img)
    sw = sw if sw is not None else max(4, size // 9)
    widths = [d.textlength(t, font=font(int(size * k))) for t, _, k in parts]
    x = (W - sum(widths)) / 2
    base = y + size
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    for (t, c, k), w in zip(parts, widths):
        f = font(int(size * k)); asc = f.getmetrics()[0]
        sd.text((x + 4, base - asc + 6), t, font=f, fill=(0, 0, 0, 150), stroke_width=sw, stroke_fill=(0, 0, 0, 150))
        x += w
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img)
    x = (W - sum(widths)) / 2
    for (t, c, k), w in zip(parts, widths):
        f = font(int(size * k)); asc = f.getmetrics()[0]
        d.text((x, base - asc), t, font=f, fill=c, stroke_width=sw, stroke_fill=INK)
        x += w

def telop(lines, y=1120, size=64):
    img = canvas()
    for i, s in enumerate(lines):
        text_center(img, y + i * int(size * 1.35), s, size)
    return img

# 薬剤の箱（オープニングに並べる）: (名前, 素材, 切り抜き範囲)
BOXES = [
    ("グレー\nパール13", ("IMG_7199.MOV", 7.0), (410, 660, 690, 860)),
    ("グレー", ("IMG_7204.heic", None), (460, 1512, 1388, 2368)),
    ("ブルー", ("IMG_7206.heic", None), (800, 1680, 1564, 2312)),
    ("ジェット\nパープル", ("IMG_7205.heic", None), (668, 1512, 1572, 2448)),
    ("14\nライトナー", ("IMG_7202.heic", None), (800, 1448, 1660, 2360)),
]

def load_box(src, box):
    name, ss = src
    path = os.path.join(RAW, name)
    if ss is not None:   # 動画から1コマ
        png = os.path.join(WORK, "box_frame.png")
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-i", path, "-frames:v", "1", png])
        im = Image.open(png)
    else:
        import pillow_heif; pillow_heif.register_heif_opener()
        from PIL import ImageOps
        im = ImageOps.exif_transpose(Image.open(path))
    return im.convert("RGB").crop(box)

def chips(img, y=1330):
    d = ImageDraw.Draw(img)
    h, gap = 150, 22
    tiles = []
    for name, src, box in BOXES:
        b = load_box(src, box)
        w = int(b.width * h / b.height)
        tiles.append((name, b.resize((w, h), Image.LANCZOS)))
    total = sum(t.width for _, t in tiles) + gap * (len(tiles) - 1)
    x = (W - total) / 2
    f = font(28)
    for name, t in tiles:
        x0 = int(x)
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([x0 + 4, y + 8, x0 + t.width + 4, y + h + 8], 14, fill=(0, 0, 0, 130))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
        mask = Image.new("L", t.size, 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, t.width - 1, h - 1], 14, fill=255)
        img.paste(t, (x0, y), mask)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([x0, y, x0 + t.width, y + h], 14, outline=WHITE, width=4)
        for j, ln in enumerate(name.split("\n")):
            w = d.textlength(ln, font=f)
            d.text((x0 + (t.width - w) / 2, y + h + 12 + j * 34), ln, font=f, fill=WHITE, stroke_width=4, stroke_fill=INK)
        x += t.width + gap

def title(img, y=230):
    rich_center(img, y, [("この冬", WHITE, 1.0), ("1番人気", GOLD, 1.25), ("オーダー", WHITE, 1.0)], 70)
    text_center(img, y + 120, "マロングレージュ", 118, fill=MARRON, sw=12)

def save(img, name):
    p = os.path.join(WORK, name); img.save(p); return p

# ---------- 色相環アニメーション ----------
WHEEL_SRC = os.path.join(RAW, "色相環.jpg")
CX, CY, RMID = 498, 545, 278          # 元画像の円の中心と帯の中ほどの半径
WX, WY = 40, 330 - 110                # 元画像(上110px切り落とし)を置く位置

def wheel_pos(deg, r=RMID):
    a = math.radians(deg)
    return (WX + CX + r * math.sin(a), WY + CY - r * math.cos(a))

# 色相環上の角度（黄=0から時計回り30度ずつ）
DEG = {"黄": 0, "緑": 60, "青": 120, "紫": 180, "赤": 240, "赤橙": 270, "橙": 300}

def arrow(d, p0, p1, col, width=14, head=40):
    d.line([p0, p1], fill=col, width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    a1, a2 = ang + math.radians(150), ang - math.radians(150)
    d.polygon([p1, (p1[0] + head * math.cos(a1), p1[1] + head * math.sin(a1)),
               (p1[0] + head * math.cos(a2), p1[1] + head * math.sin(a2))], fill=col)

def shorten(p0, p1, s0, s1):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy)
    return ((p0[0] + dx * s0 / L, p0[1] + dy * s0 / L), (p1[0] - dx * s1 / L, p1[1] - dy * s1 / L))

def wheel_frames(dur=4.2):
    T1, T2, T3 = 0.3, 1.5, 2.8   # 赤丸 → 補色の矢印 → 緑に✕
    src = Image.open(WHEEL_SRC).convert("RGBA").crop((0, 110, 1000, 1000))
    bg = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    bg.alpha_composite(src, (WX, WY + 110))
    d = os.path.join(WORK, "wheel"); os.makedirs(d, exist_ok=True)
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS
        im = bg.copy(); dr = ImageDraw.Draw(im)
        text_center(im, 110, "色相環で選定", 72)
        # 1) 赤は残す
        if t >= T1:
            k = min(1, (t - T1) / 0.3)
            for key in ("赤", "赤橙"):
                x, y = wheel_pos(DEG[key]); r = 82 * (0.6 + 0.4 * k)
                dr.ellipse([x - r, y - r, x + r, y + r], outline=(230, 20, 30, 255), width=12)
        # 2) 補色で打ち消す
        if t >= T2:
            k = min(1, (t - T2) / 0.4)
            for a, b, col in (("橙", "青", (30, 70, 170, 255)), ("黄", "紫", (100, 40, 140, 255))):
                p0, p1 = shorten(wheel_pos(DEG[a], 250), wheel_pos(DEG[b], 250), 60, 60)
                p1 = (p0[0] + (p1[0] - p0[0]) * k, p0[1] + (p1[1] - p0[1]) * k)
                arrow(dr, p0, p1, col)
        # 3) 緑は使わない
        if t >= T3:
            gx, gy = wheel_pos(DEG["緑"])
            arrow(dr, (1040, 290), (gx + 70, gy - 60), (230, 20, 30, 255), width=12)
            k = min(1, (t - T3) / 0.25); sz = 70 * (1.6 - 0.6 * k)
            dr.line([(gx - sz, gy - sz), (gx + sz, gy + sz)], fill=(230, 20, 30, 255), width=22)
            dr.line([(gx - sz, gy + sz), (gx + sz, gy - sz)], fill=(230, 20, 30, 255), width=22)
        # 下のテロップ
        if T1 <= t < T2:
            lines = ["髪の中の「赤」は", "削らないで残す"]
        elif T2 <= t < T3:
            lines = ["オレンジには「ブルー」", "黄みには「パープル」で打ち消す"]
        elif t >= T3:
            lines = ["だから緑系は使いません", "緑っぽくならない"]
        else:
            lines = []
        for j, s in enumerate(lines):
            text_center(im, 1300 + j * 92, s, 66)
        im.convert("RGB").save(os.path.join(d, f"{i:04d}.png"))
    return d

# ---------- 混ぜるアニメーション ----------
def mix_frames(dur=2.8):
    d = os.path.join(WORK, "mix"); os.makedirs(d, exist_ok=True)
    items = [("髪の中の赤", (190, 45, 40)), ("ブルー", (40, 90, 185)),
             ("ジェットパープル", (105, 45, 145)), ("グレー", (120, 120, 124))]
    starts = [(250, 650), (830, 650), (250, 1150), (830, 1150)]
    center = (540, 900); result = (132, 112, 96)
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS
        im = Image.new("RGBA", (W, H), (255, 255, 255, 255)); dr = ImageDraw.Draw(im)
        text_center(im, 230, "髪の暖色 ＋ 寒色", 76)
        k = min(1, max(0, (t - 0.5) / 1.0)); k = k * k * (3 - 2 * k)
        if k < 1:
            for (name, col), (sx, sy) in zip(items, starts):
                x = sx + (center[0] - sx) * k; y = sy + (center[1] - sy) * k; r = 150 * (1 - 0.6 * k)
                dr.ellipse([x - r, y - r, x + r, y + r], fill=col + (235,))
                if k < 0.3:
                    f = font(34); w = dr.textlength(name, font=f)
                    dr.text((x - w / 2, y + r + 14), name, font=f, fill=WHITE, stroke_width=5, stroke_fill=INK)
        if t >= 1.5:
            g = min(1, (t - 1.5) / 0.5); r = 120 + 140 * g
            dr.ellipse([center[0] - r, center[1] - r, center[0] + r, center[1] + r], fill=result + (255,))
            if t >= 1.9:
                text_center(im, 1250, "＝ マロングレージュ", 84, fill=MARRON, sw=10)
        im.convert("RGB").save(os.path.join(d, f"{i:04d}.png"))
    return d

# ---------- レシピカード ----------
def recipe_card():
    img = canvas(); d = ImageDraw.Draw(img)
    d.rounded_rectangle([50, 300, 1030, 1560], 36, fill=(30, 22, 18, 200))
    text_center(img, 340, "レシピ選定はこちら", 58, fill=GOLD, sw=6, shadow=False)
    f1, f2, f3 = font(40), font(36), font(30)
    y = 450
    d.text((90, y), "ベース", font=f2, fill=GOLD)
    d.text((90, y + 50), "グレーパール13 ＋ グレー20%", font=f1, fill=WHITE)
    y += 140
    rows = [
        ("① 根元", "ベース ＋ ブルー10%", "OX 6%"),
        ("② 中間", "ベース", "OX 3%"),
        ("③ 毛先（黄み）", "ベース ＋ ジェットパープル10%", "OX 3%"),
        ("④ 襟足・耳上（暗い所）", "14ライトナー ＋ ①の薬 1:1", "OX 6%"),
    ]
    for head, body, ox in rows:
        d.line([(90, y - 14), (990, y - 14)], fill=(255, 255, 255, 70), width=2)
        d.text((90, y), head, font=f2, fill=GOLD)
        ow = d.textlength(ox, font=f1)
        d.rounded_rectangle([990 - ow - 24, y - 4, 990, y + 52], 26, fill=(215, 175, 120, 255))
        d.text((990 - ow - 12, y), ox, font=f1, fill=(40, 28, 20))
        d.text((90, y + 54), body, font=f1, fill=WHITE)
        y += 150
    y += 10
    for s in ["グレーパール13：アディクシーカラー", "グレー：アジアンカラーフェス",
              "ジェットパープル9：キラテラ", "14ライトナー：フィヨーレ"]:
        d.text((90, y), s, font=f3, fill=(225, 215, 200)); y += 42
    return img

# ---------- 動画の組み立て ----------
def run(cmd):
    subprocess.run(cmd, check=True)

ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]

def clip(name, src, ss, dur, vf, overlays, speed=1.0):
    """overlays=[(png, 開始秒, 終了秒)]"""
    out = os.path.join(WORK, name)
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-t", str(dur * speed), "-i", src]
    for p, _, _ in overlays:
        cmd += ["-i", p]
    chain = f"[0:v]{vf},setpts=PTS/{speed},fps={FPS},format=rgba[v0]"
    for i, (_, a, b) in enumerate(overlays):
        chain += f";[v{i}][{i+1}:v]overlay=0:0:enable='between(t,{a},{b})'[v{i+1}]"
    cmd += ["-filter_complex", chain, "-map", f"[v{len(overlays)}]", "-t", str(dur)] + ENC + [out]
    run(cmd); return out

def seq(name, folder):
    out = os.path.join(WORK, name)
    run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(folder, "%04d.png")] + ENC + [out])
    return out

def main():
    shutil.rmtree(WORK, ignore_errors=True); os.makedirs(WORK)
    R = lambda f: os.path.join(RAW, f)
    vertical = f"scale={W}:{H}"
    # お客様の掲載許可あり → ぼかしなし
    crop_land = lambda x: f"crop=608:1080:{x}:0,scale={W}:{H}"

    # 1 オープニング：仕上がり＋タイトル＋薬剤チップ
    op = canvas(); title(op); chips(op)
    c1 = clip("c1.mp4", R("IMG_6726.mov"), 0, 3.6, vertical, [(save(op, "op.png"), 0, 99)])
    # 2 ビフォー
    c2 = clip("c2.mp4", R("IMG_6716.MOV"), 0.2, 3.6, crop_land(760), [
        (save(telop(["今回はこちらからスタート"]), "t2a.png"), 0, 1.8),
        (save(telop(["根元は暗く", "毛先はオレンジ・黄み"]), "t2b.png"), 1.8, 99)])
    # 3 色相環
    c3 = seq("c3.mp4", wheel_frames())
    # 4 レシピ（箱を積む映像の上に）
    c4 = clip("c4.mp4", R("IMG_7199.MOV"), 1.8, 6.0, vertical, [
        (save(telop(["4カップで塗り分け"], y=150, size=76), "t4a.png"), 0, 99),
        (save(recipe_card(), "t4b.png"), 0.6, 99)])
    # 5 塗布（2倍速）
    c5 = clip("c5.mp4", R("IMG_6721.MOV"), 4.0, 4.0, crop_land(700), [
        (save(telop(["ベースの茶色さに合わせて", "場所ごとに塗り分け"]), "t5a.png"), 0, 2.0),
        (save(telop(["実はブラウンの薬は", "ゼロ"]), "t5b.png"), 2.0, 99)], speed=2.0)
    # 6 混ぜる
    c6 = seq("c6.mp4", mix_frames())
    # 7 アフター（揺らす）
    c7 = clip("c7.mp4", R("IMG_6729.MOV"), 0, 4.8, vertical, [
        (save(telop(["こっくり見えるのに", "透明感うるうる"]), "t7a.png"), 0, 2.4),
        (save(telop(["緑にならず", "顔色が明るく見える"]), "t7b.png"), 2.4, 99)])
    # 8 エンディング：一番人気の仕上がり
    ed1 = canvas(); title(ed1)
    ed1.alpha_composite(telop(["ベースに合わせた塗り分けだから", "次のカラーもこの発色"], size=58))
    ed2 = canvas(); title(ed2)
    ed2.alpha_composite(telop(["保存して活用してください"], size=66))
    c8 = clip("c8.mp4", R("IMG_6726.mov"), 0.4, 4.4, vertical, [
        (save(ed1, "ed1.png"), 0, 2.4), (save(ed2, "ed2.png"), 2.4, 99)])

    lst = os.path.join(WORK, "list.txt")
    with open(lst, "w") as f:
        for c in (c1, c2, c3, c4, c5, c6, c7, c8):
            f.write(f"file '{c}'\n")
    out = os.path.join(OUT, "reel1_マロングレージュ.mp4")
    # 無音の音声トラックを付ける（音楽はインスタで追加）
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
         "-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart", out])
    print(out)

if __name__ == "__main__":
    main()
