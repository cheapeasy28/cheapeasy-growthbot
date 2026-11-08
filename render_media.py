"""Build branded static image assets from approved product topics.
Generated media belongs in public GitHub repo so Buffer can fetch the image by URL.
"""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent
PRODUCTS = json.loads((ROOT / 'products.json').read_text(encoding='utf-8'))
MEDIA = ROOT / 'media'
MEDIA.mkdir(exist_ok=True)

THEMES = {
    'gold': ((7, 13, 25), (33, 27, 19), (255, 193, 55), (255, 231, 181)),
    'blue': ((7, 17, 48), (12, 47, 74), (52, 217, 250), (218, 250, 255)),
    'teal': ((4, 27, 44), (9, 58, 66), (61, 231, 211), (228, 255, 248)),
}
SIZES = {'pinterest': (1000, 1500), 'instagram': (1080, 1350), 'facebook': (1200, 630)}
FONTS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    'C:/Windows/Fonts/arialbd.ttf',
]
REGULAR = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    'C:/Windows/Fonts/arial.ttf',
]

def font(size, bold=True):
    for fp in (FONTS if bold else REGULAR):
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()

def wrap(draw, s, f, maxwidth):
    lines, current = [], ''
    for word in s.split():
        test = f'{current} {word}'.strip()
        if draw.textbbox((0, 0), test, font=f)[2] <= maxwidth:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines

def gradient_bg(w, h, a, b, accent):
    import numpy as np
    yy, xx = np.ogrid[:h, :w]
    t = np.clip((yy/h)*0.58+(xx/w)*0.4, 0, 1)
    glow = np.maximum(0, 1-np.sqrt(((xx/w)-0.86)**2+((yy/h)-0.27)**2)*2.8)*0.13
    base = np.empty((h,w,3),dtype=np.uint8)
    for i in range(3):
        base[:,:,i] = np.clip(a[i]*(1-t)+b[i]*t+accent[i]*glow,0,255).astype(np.uint8)
    return Image.fromarray(base,'RGB')

def place_book(canvas, key, rect):
    book = Image.open(ROOT / 'covers' / f'{key}.png').convert('RGBA')
    bw, bh = int(rect[2]), int(rect[3])
    book.thumbnail((bw, bh), Image.Resampling.LANCZOS)
    bx, by = int(rect[0] + (bw-book.width)/2), int(rect[1]+(bh-book.height)/2)
    shadow = Image.new('RGBA', canvas.size)
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((bx-8, by-8, bx+book.width+8, by+book.height+8), radius=28, fill=(0,0,0,165))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(book,(bx,by))

def make(key, cfg, tip_idx, channel):
    w,h = SIZES[channel]
    a,b,accent,light = THEMES[cfg['colour']]
    bg=gradient_bg(w,h,a,b,accent).convert('RGBA')
    d=ImageDraw.Draw(bg)
    # decorative highlights; keep all readable text in safe margins.
    d.ellipse((w*.54, h*-.19,w*1.38,h*.55),outline=(*accent,95),width=max(3,w//170))
    d.ellipse((w*.63, h*-.08,w*1.17,h*.38),outline=(*accent,45),width=max(2,w//300))
    for j in range(12):
        xx=int(w*.09+(j%4)*w*.058)
        yy=int(h*.78+(j//4)*h*.024)
        d.ellipse((xx,yy,xx+4,yy+4),fill=(*accent,60))
    margin=int(w*.075)
    if channel == 'facebook':
        fs_tag,fs_head,fs_small=18,48,21
        d.rounded_rectangle((margin,40,margin+390,78),radius=14,fill=(*accent,240))
        d.text((margin+18,48),'CHEAP&EASY  /  DIGITAL GUIDES',font=font(fs_tag),fill=(7,18,32))
        headline=cfg['tips'][tip_idx]['hook']
        lines=wrap(d,headline,font(fs_head),640)
        yy=120
        for line in lines[:3]:
            d.text((margin,yy),line,font=font(fs_head),fill=(250,253,255),stroke_width=0)
            yy+=64
        d.rounded_rectangle((margin,365,690,470),radius=20,fill=(4,22,34,255),outline=(*accent,120),width=2)
        d.text((margin+20,383),'USEFUL TIPS, PRINTABLE TOOLS',font=font(19),fill=light)
        d.text((margin+20,423),cfg['label'][:34],font=font(18,bold=False),fill=(228,230,242))
        d.text((margin,h-86),'CHEAP&EASY  •  FIND THE GUIDE ON WHOP',font=font(19),fill=light)
        place_book(bg,key,(750,107,390,380))
        d=ImageDraw.Draw(bg)
        d.rounded_rectangle((742,505,1150,550),radius=20,fill=(*accent,220))
        d.text((780,515),'SAVE THE CHECKLIST IDEA',font=font(19),fill=(5,19,32))
    else:
        tag_f=font(20)
        d.rounded_rectangle((margin,48,w-margin,100),radius=24,fill=(*accent,234))
        d.text((margin+25,61),'CHEAP&EASY   |   PRACTICAL DIGITAL GUIDES',font=tag_f,fill=(8,17,28))
        d.text((margin,137),cfg['label'],font=font(21),fill=light)
        # readable hook at top before the book; avoid small lettering.
        headline=cfg['tips'][tip_idx]['hook']
        f=font(55 if channel=='pinterest' else 57)
        lines=wrap(d,headline,f,w-2*margin)
        yy=198
        for line in lines[:3]:
            d.text((margin,yy),line,font=f,fill=(255,255,255))
            yy+=78
        # central cover intentionally small inside frame, not edge-to-edge.
        top=max(425,yy+16)
        cover_h=650 if channel=='pinterest' else 555
        place_book(bg,key,(w*.21,top,w*.58,cover_h))
        d=ImageDraw.Draw(bg)
        ribbon_y=h-248
        d.rounded_rectangle((margin,ribbon_y,w-margin,ribbon_y+96),radius=18,fill=(3,12,24,202),outline=(*accent,160),width=3)
        d.text((margin+26,ribbon_y+21),'GUIDE + REUSABLE WORKSHEETS',font=font(26),fill=light)
        d.text((margin+26,ribbon_y+58),'Practical UK digital download',font=font(21,False),fill=(245,247,252))
        d.line((margin,h-110,w-margin,h-110),fill=(*accent,200),width=3)
        d.text((margin,h-95),'SEE THE CHEAP&EASY GUIDE ON WHOP',font=font(23),fill=(245,248,252))
    file=MEDIA / f'{key}_{tip_idx:02d}_{channel}.jpg'
    bg.convert('RGB').save(file,quality=82,optimize=True,subsampling=0)
    return file

if __name__=='__main__':
    n=0
    for key,cfg in PRODUCTS.items():
        for i,_ in enumerate(cfg['tips']):
            for chan in SIZES:
                make(key,cfg,i,chan)
                n+=1
    print(f'Rendered {n} images to {MEDIA}')
