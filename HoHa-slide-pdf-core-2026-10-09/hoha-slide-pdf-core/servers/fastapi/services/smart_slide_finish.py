"""Deterministic finishing and image assignment checks shared by Smart workers."""
import html,re
import json
from html.parser import HTMLParser


def numeric_fidelity_issues(markup: str, record: dict, assets: list[dict]) -> list[str]:
    """Reject new visible amounts; semantic periods/qualifiers still need the critic."""
    class Text(HTMLParser):
        def __init__(self):super().__init__();self.parts=[];self.skip=0
        def handle_starttag(self,tag,attrs):
            if tag in {'script','style'}:self.skip+=1
        def handle_endtag(self,tag):
            if tag in {'script','style'}:self.skip=max(0,self.skip-1)
        def handle_data(self,value):
            if not self.skip:self.parts.append(value)
    text=Text();text.feed(markup)
    pattern=r'(?<!\w)(?:\d+(?:[.,]\d+)+|\d{3,})(?!\w)'
    # Decimal comma and point are equivalent. Removing separators entirely made
    # a visible section label 4.1 look like an invented value 41 (and could let
    # an actual 41 pass as 4.1).
    values=lambda value:{m.replace(',','.') for m in re.findall(pattern,value)}
    approved=' '.join(str(record.get(k,'')) for k in ('section_id','title','takeaway','content_markdown'))
    for a in assets:
        if a.get('asset_role')=='source_table':approved+=' '+json.dumps(a.get('required_table_cells',a.get('table_rows',[])),ensure_ascii=False)
    unexpected=values(' '.join(text.parts))-values(approved)
    return ['Số liệu hiển thị không có trong nội dung đã duyệt: '+v for v in sorted(unexpected)]


def image_assignment_issues(markup: str, assets: list[dict], logo_url: str='') -> list[str]:
    allowed={a['url'] for a in assets if a.get('url') and a.get('asset_role') not in {'source_reference','source_table','source_diagram'}
             and a.get('capture_mode') not in {'front_matter','page_reference'}}
    if logo_url:allowed.add(logo_url)
    class Images(HTMLParser):
        def __init__(self):super().__init__();self.urls=[]
        def handle_starttag(self,tag,attrs):
            attributes=dict(attrs)
            if tag=='img':self.urls.append(attributes.get('src',''))
            if tag=='image':self.urls.append(attributes.get('href',attributes.get('xlink:href','')))
            self.css_urls(attributes.get('style',''))
        def css_urls(self,value):
            for match in re.finditer(r'url\(\s*([\"\']?)(.*?)\1\s*\)',value,re.I):
                url=match.group(2).strip()
                if url and not url.startswith('#'):self.urls.append(url)
        def handle_data(self,value):
            self.css_urls(value)
    images=Images();images.feed(markup)
    return ['Ảnh không thuộc phân bổ riêng của slide: '+u for u in images.urls if u not in allowed]


def editorial_frame(markup: str, dna, index: int) -> str:
    """Brand-neutral geometry in safe margins; no raster assets or fake logos."""
    if 'data-editorial-frame' in markup:return markup
    match=re.search(r'<section\b[^>]*>',markup,re.I)
    if not match:return markup
    tag=match.group();accent=html.escape(dna.palette.accent,quote=True)
    tag=tag.replace('style="','style="position:relative;isolation:isolate;',1)
    decoration=(f'<svg data-editorial-frame="true" aria-hidden="true" width="1280" height="720" viewBox="0 0 1280 720" '
        f'style="position:absolute;inset:0;pointer-events:none;z-index:-1" xmlns="http://www.w3.org/2000/svg">'
        f'<path d="M1040 0H1280V150Z" fill="{accent}" opacity="0.09"/>'
        f'<path d="M1150 0H1280V90Z" fill="{accent}" opacity="0.16"/>'
        f'<path d="M0 585V720H190Z" fill="{accent}" opacity="0.055"/>'
        f'<path d="M24 56V664M24 664H88" fill="none" stroke="{accent}" stroke-width="2" opacity="0.45"/>'
        + (f'<path d="M950 -40Q720 260 960 760H1350V-40Z" fill="{accent}" opacity=".035"/>' if index%3==0 else
           f'<circle cx="1290" cy="380" r="350" fill="none" stroke="{accent}" stroke-width="90" opacity=".035"/>' if index%3==1 else
           f'<path d="M860 0L1280 620M1000 0L1280 400" fill="none" stroke="{accent}" stroke-width="90" opacity=".035"/>')+
        '</svg>')
    return markup[:match.start()]+tag+decoration+markup[match.end():]
