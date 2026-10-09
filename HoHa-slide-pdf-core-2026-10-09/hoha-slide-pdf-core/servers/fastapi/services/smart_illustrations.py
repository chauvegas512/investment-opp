"""Offline Iconify SVG illustrations: no invented logos, measurements or photos."""
import html,json,unicodedata,re
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=1)
def catalog():
    return json.loads((Path(__file__).resolve().parents[1]/'assets/iconify/lucide-curated.json').read_text(encoding='utf-8'))

def icon(name, color='currentColor', size=32):
    data=catalog();item=data['icons'].get(name,data['icons']['layers'])
    return f'<svg data-iconify="lucide:{html.escape(name,quote=True)}" width="{size}" height="{size}" viewBox="0 0 {item.get("width",data["width"])} {item.get("height",data["height"])}" fill="none" style="color:{html.escape(color,quote=True)};flex-shrink:0" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">{item["body"]}</svg>'

def subject_icons(record):
    text=' '.join(str(record.get(k,'')) for k in ('title','content_markdown'))
    text=''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn').replace('đ','d')
    rules=[(('cloud','aws','dam may'),'cloud'),(('du lieu','data'),'database'),(('ai','cong nghe'),'server'),
           (('mobile','ung dung','dien thoai'),'smartphone'),(('dau tu','chung khoan'),'briefcase-business'),
           (('the tin dung','credit'),'credit-card'),(('bao hiem','rui ro','bao mat'),'shield-check'),
           (('khach hang','ca nhan'),'users'),(('sinh loi','tien gui','thanh toan'),'wallet'),
           (('he sinh thai','ket noi'),'network'),(('ngan hang','bank'),'landmark'),(('esg','ben vung'),'leaf')]
    chosen=[]
    for words,name in rules:
        if any((bool(re.search(r'(?<!\w)ai(?!\w)',text)) if word=='ai' else word in text) for word in words) and name not in chosen:chosen.append(name)
    return chosen[:3] or ['layers','target','globe']

def illustration_panel(record,dna,index):
    """An illustrative vignette, explicitly labelled; not evidence or a brand asset."""
    names=subject_icons(record);p=dna.palette
    accent=html.escape(p.accent,quote=True);ink=html.escape(p.ink,quote=True)
    satellites=''.join(f'<div style="position:absolute;left:{12+i*29}%;top:{62 if i%2==0 else 73}%;padding:18px;border-radius:24px;background:{p.canvas};color:{p.accent};box-shadow:0 12px 30px #0000000c">{icon(name,p.accent,40)}</div>' for i,name in enumerate(names[1:]))
    return (f'<figure data-generated-illustration="true" style="margin:0;position:relative;min-height:240px;height:100%;overflow:hidden;border-radius:32px;background:linear-gradient({125+index%4*15}deg,{p.muted},{p.canvas});border:1px solid {accent}30">'
        f'<svg aria-hidden="true" viewBox="0 0 500 420" preserveAspectRatio="none" style="position:absolute;width:100%;height:100%;inset:0" xmlns="http://www.w3.org/2000/svg"><circle cx="320" cy="180" r="160" fill="{accent}" opacity=".08"/><path d="M-30 340Q160 200 340 390T570 310" fill="none" stroke="{accent}" stroke-width="42" opacity=".05"/><path d="M40 80H110M40 80V145M455 345H390M455 345V280" fill="none" stroke="{accent}" stroke-width="2" opacity=".35"/></svg>'
        f'<div style="position:absolute;inset:14% 15% 30%;display:flex;align-items:center;justify-content:center;color:{ink}">{icon(names[0],p.accent,160)}</div>{satellites}'
        f'<figcaption style="position:absolute;bottom:22px;left:28px;font-size:14px;color:{ink};opacity:.65">Minh họa</figcaption></figure>')
