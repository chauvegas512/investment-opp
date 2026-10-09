"""Conservative deterministic layout compiler. Never trims approved content."""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse
from dataclasses import dataclass

from services.presentation_dna import PresentationDNA
from services.smart_image_composition import is_interface_asset, photo_frame
from services.smart_slide_finish import editorial_frame
from services.smart_illustrations import illustration_panel,icon,subject_icons
from services.smart_product_showcase import render_four_product_showcase


@dataclass(frozen=True)
class LayoutChoice:
    archetype: str
    variant: str


def choose_layout(record: dict, assets: list[dict], index: int) -> LayoutChoice:
    if any(a.get("asset_role") in {"source_evidence","source_table"} for a in assets):
        return LayoutChoice("source_visual", "wide_evidence")
    if record.get('layout_spec'):
        return LayoutChoice('diagram' if record['layout_spec'].get('kind')=='flow' else 'comparison','grouped_copy')
    form = record.get("visual_form")
    if form == "toc":
        return LayoutChoice("editorial", "agenda")
    if form == "title":
        return LayoutChoice("cover", "editorial_cover")
    if form == "closing":
        return LayoutChoice("editorial", "closing_statement")
    if form in {"table", "comparison"}:
        return LayoutChoice("comparison", "striped_table")
    if form in {"diagram", "process", "timeline"}:
        return LayoutChoice("diagram", "connected_nodes")
    if form == 'photo':
        if (record.get('section_id') and record.get('title','').strip().casefold()
                == record.get('section_title','').strip().casefold()
                and len(record.get('content_markdown','').split()) <= 55):
            return LayoutChoice('editorial','chapter_opener')
        return LayoutChoice('editorial','photo_split')
    return LayoutChoice("kpi" if re.search(r"\d[\d.,]*\s*(?:%|triệu|tỷ|million|billion)", record.get("content_markdown", "")) else "editorial",
        "split" if index % 2 else "wide")


def _inline(value: str) -> str:
    # No raw HTML, links, scripts or user-controlled CSS can enter code layouts.
    value = html.escape(value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", value)
    return value


def _copy(markdown: str, *, size: int = 22, gap: int = 12) -> str | None:
    if re.search(r"```|!\[|<[^>]+>|\$|\\\(|\\\[|^\s*\|", markdown, re.M):
        return None  # complex formulas/tables go to the existing designer unchanged
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    cleaned = [re.sub(r"^[#*-]+\s+", "", line) for line in lines]
    return "".join(f'<p style="margin:0 0 {gap}px;font-size:{size}px;line-height:1.35;break-inside:avoid">{_inline(line)}</p>' for line in cleaned)


def _columns(copy: str) -> str:
    # Explicit columns prevent a paragraph from being fragmented across columns
    # and make both browser geometry and projection reading deterministic.
    paragraphs = re.findall(r'<p\b.*?</p>',copy,re.S)
    weights = [len(re.sub(r'<[^>]+>','',p)) for p in paragraphs]
    split = min(range(1,len(paragraphs)),key=lambda i:abs(sum(weights[:i])-sum(weights[i:]))) if len(paragraphs)>1 else 1
    return '<div style="display:grid;grid-template-columns:1fr 1fr;gap:40px">' + ''.join('<div>'+''.join(group)+'</div>' for group in (paragraphs[:split],paragraphs[split:]))+'</div>'


def _image_credit(source: str) -> str:
    return f'<figcaption style="font-size:12px;height:20px;line-height:20px;white-space:nowrap"><a href="{html.escape(source,quote=True)}" style="color:inherit">Ảnh: {html.escape(urlparse(source).hostname or "Nguồn thương hiệu")}</a></figcaption>'


def _private_photo_credits(value: str, assets: list[dict]) -> str:
    for asset in assets:
        if asset.get('display_credit') is False and asset.get('url'):
            url=re.escape(html.escape(asset['url'],quote=True))
            value=re.sub(r'(<img\b[^>]*\bsrc="'+url+r'"[^>]*>)\s*<figcaption\b[^>]*>.*?</figcaption>',r'\1',value,flags=re.S)
    return value


def _agenda(markdown: str, dna: PresentationDNA) -> str | None:
    """Ordered source chapters, with no invented headings or truncated copy."""
    lines=[line.strip() for line in markdown.splitlines() if line.strip()]
    if not 3<=len(lines)<=8: return None
    items=[re.fullmatch(r'(\d+)\.(?:1\.)?\s+(.+)',line) for line in lines]
    if any(item is None for item in items): return None
    if [int(item[1]) for item in items]!=list(range(1,len(items)+1)): return None
    p=dna.palette
    rows=[]
    for item in items:
        # For chapter 4.1 the prefix belongs to the source copy, not a new chapter.
        number=item[1]
        text=re.sub(r'^\d+\.\s+','',item[0])
        shade=p.muted if number in {'4','5','6'} else 'transparent'
        rows.append(f'<li style="list-style:none;display:grid;grid-template-columns:44px minmax(0,1fr);gap:18px;align-items:center;background:{shade};padding:6px 12px;position:relative"><span style="font-size:28px;line-height:1.15;font-weight:800;color:{p.accent};background:{p.canvas};z-index:1">{number}</span><div style="font-size:20px;line-height:1.25">{_inline(text)}</div></li>')
    return f'<ol style="margin:0;padding:0;position:relative;display:grid;gap:5px"><span aria-hidden="true" style="position:absolute;top:12px;bottom:12px;left:26px;border-left:2px solid {p.ink}"></span>'+''.join(rows)+'</ol>'


def _editorial_cover(record: dict, dna: PresentationDNA, total: int, assets: list[dict] | None = None) -> dict | None:
    """Real product hero and a bounded metadata footer; no generated app UI."""
    photos=[a for a in assets or [] if a.get('asset_role')=='subject_reference' and a.get('url')]
    if not (photos or dna.brand_images) or len(record.get('content_markdown','').split())>100:
        return None
    markdown=record.get('content_markdown','')
    lines=[re.sub(r'^[-#]+\s+','',line.strip()) for line in markdown.splitlines() if line.strip()]
    member=next((i for i,line in enumerate(lines) if re.match(r'^\*\*(?:Thành viên|Members|Presenters)',line,re.I)),None)
    if member is not None:
        markdown=' · '.join(lines[:member])+'\n'+' · '.join(lines[member:])
    copy=_copy(markdown,size=14,gap=3)
    if copy is None: return None
    instruction=record.get('visual_instruction','')
    image=next((item for item in dna.brand_images if item.url in instruction),None)
    if image is None:
        image=max(dna.brand_images,key=lambda item:bool(re.search(r'man-hinh|screenshot|screen|phone|handset',item.label,re.I))) if dna.brand_images else None
    photo=next((a for a in photos if a.get('selected')),None)
    if photo is None: photo=image.model_dump() if image else photos[0]
    photo=next((a for a in photos if a['url']==photo['url']),photo)
    treatment=record.get('image_treatment','auto')
    hero=photo_frame(photo,'diagonal' if treatment=='auto' else treatment)
    credit='' if photo.get('display_credit') is False else _image_credit(photo.get('source_url',''))
    label_match=re.search(r'(?:nhãn(?: nhỏ)?|labels?)\s*[:]?\s*(.+)',instruction,re.I)
    labels=re.findall(r'[“"]([^”"]{2,24})[”"]',label_match[1])[:3] if label_match else []
    connectors=''
    if len(labels)==3:
        connectors=f'<div style="border-top:1px solid {dna.palette.accent};display:flex;justify-content:space-around;padding-top:10px;font-size:16px">'+''.join(f'<span style="position:relative"><span aria-hidden="true" style="position:absolute;top:-15px;left:50%;width:1px;height:12px;background:{dna.palette.accent}"></span>{_inline(label)}</span>' for label in labels)+'</div>'
    title=record.get('title','');p=dna.palette
    logo=f'<img src="{html.escape(dna.logo_url,quote=True)}" alt="Brand logo" style="width:170px;height:36px;object-fit:contain">' if dna.logo_enabled and dna.logo_url else ''
    result=f'''<section class="relative h-[720px] w-[1280px] overflow-hidden" data-slide-type="title" data-slide-title="{html.escape(title,quote=True)}" data-source-evidence="{html.escape(' '.join(record.get('source_evidence_ids',[])),quote=True)}" data-layout-archetype="cover" data-dna-hash="{dna.fingerprint()}" style="width:1280px;height:720px;box-sizing:border-box;padding:{dna.safe_margin}px;background:{p.canvas};color:{p.ink};font-family:'{dna.font_family}',sans-serif;display:grid;grid-template-rows:36px minmax(0,1fr) auto;gap:20px;overflow:hidden">
<header style="display:flex;align-items:center;justify-content:space-between">{logo}<span style="font-size:14px;color:{p.accent}">01 / {total:02d}</span></header>
<main style="display:grid;grid-template-columns:1fr 1fr;gap:44px;min-height:0"><div style="display:flex;flex-direction:column;justify-content:center"><div aria-hidden="true" style="width:64px;height:5px;background:{p.accent};margin-bottom:22px"></div><h1 style="font-size:52px;font-weight:800;line-height:1.08;margin:0 0 24px">{_inline(title)}</h1><p style="font-size:22px;line-height:1.4;margin:0">{_inline(record.get('takeaway',''))}</p></div><div style="min-height:0;display:grid;grid-template-rows:minmax(0,1fr) auto auto;gap:8px">{hero}{connectors}{credit}</div></main>
<footer style="border-top:1px solid #DDE3E7;padding-top:10px">{_columns(copy)}</footer></section>'''
    return {'html':result,'title':title,'slide_type':'title'}


def _chapter_opener(record: dict, dna: PresentationDNA, assets: list[dict],
                    index: int, total: int) -> dict | None:
    """A photo-led section break, reserved for short, explicit section starts."""
    photos=[a for a in assets if a.get('asset_role')=='subject_reference'
            and a.get('image_kind')!='logo' and a.get('url')]
    selected=[a for a in photos if a.get('selected')]
    if len(selected)>1:return None
    photo=selected[0] if selected else next((a for a in photos if not is_interface_asset(a)),
                                            photos[0] if photos else None)
    if photo is None:return None
    copy=_copy(record.get('content_markdown',''),size=19,gap=8)
    if copy is None:return None
    p=dna.palette
    title=record.get('title','')
    treatment=record.get('image_treatment','auto')
    hero=photo_frame(photo,'diagonal' if treatment=='auto' else treatment)
    if is_interface_asset(photo):
        hero=f'<div style="height:100%;box-sizing:border-box;background:{p.muted};padding:32px">{hero}</div>'
    logo=(f'<img src="{html.escape(dna.logo_url,quote=True)}" alt="Brand logo" '
          'style="width:140px;height:40px;object-fit:contain">') if dna.logo_enabled and dna.logo_url else ''
    evidence=html.escape(' '.join(record.get('source_evidence_ids',[])),quote=True)
    result=f'''<section class="relative h-[720px] w-[1280px] overflow-hidden" data-slide-type="content" data-slide-title="{html.escape(title,quote=True)}" data-layout-archetype="editorial" data-layout-variant="chapter_opener" data-source-evidence="{evidence}" data-dna-hash="{dna.fingerprint()}" style="width:1280px;height:720px;box-sizing:border-box;background:{p.canvas};color:{p.ink};font-family:'{dna.font_family}',sans-serif;position:relative;overflow:hidden">
<div style="position:absolute;inset:0 47% 0 0;background:{p.muted}">{hero}</div>
<div style="position:absolute;inset:0 0 0 53%;box-sizing:border-box;padding:{dna.safe_margin}px;display:flex;flex-direction:column;min-width:0">
<header style="height:44px;display:flex;align-items:flex-start;justify-content:space-between"><span style="font-size:22px;font-weight:800;color:{p.accent}">{_inline(record.get('section_id',''))}</span>{logo}</header>
<main style="flex:1;min-height:0;display:flex;flex-direction:column;justify-content:center"><div aria-hidden="true" style="width:72px;height:5px;background:{p.accent};margin-bottom:22px"></div><h1 style="font-size:{48 if len(title)<75 else 40}px;line-height:1.08;margin:0 0 20px;font-weight:800">{_inline(title)}</h1><p style="font-size:24px;line-height:1.3;margin:0 0 20px">{_inline(record.get('takeaway',''))}</p><div style="border-top:1px solid {p.accent};padding-top:16px">{copy}</div></main>
<footer style="font-size:14px;border-top:1px solid {p.accent};padding-top:12px;display:flex;justify-content:space-between"><span>{_inline(dna.subject[:80])}</span><span>{index+1:02d} / {total:02d}</span></footer></div></section>'''
    if any(a.get('selected') and a.get('url') not in html.unescape(result) for a in assets):
        return None
    return {'html':editorial_frame(_private_photo_credits(result,assets),dna,index),
            'title':title,'slide_type':'content'}


def _closing_statement(record: dict, dna: PresentationDNA, assets: list[dict],
                       index: int, total: int) -> dict | None:
    """Large, quiet final page; all supplied closing details stay visible."""
    if (len(record.get('content_markdown','').split())>70 or
            any(a.get('selected') or a.get('asset_role')=='source_evidence' for a in assets)):
        return None
    copy=_copy(record.get('content_markdown',''),size=20,gap=8)
    if copy is None:return None
    p=dna.palette;title=record.get('title','')
    logo=(f'<img src="{html.escape(dna.logo_url,quote=True)}" alt="Brand logo" '
          'style="width:140px;height:40px;object-fit:contain">') if dna.logo_enabled and dna.logo_url else ''
    evidence=html.escape(' '.join(record.get('source_evidence_ids',[])),quote=True)
    result=f'''<section class="relative h-[720px] w-[1280px] overflow-hidden" data-slide-type="content" data-slide-title="{html.escape(title,quote=True)}" data-layout-archetype="editorial" data-layout-variant="closing_statement" data-source-evidence="{evidence}" data-dna-hash="{dna.fingerprint()}" style="width:1280px;height:720px;box-sizing:border-box;padding:{dna.safe_margin}px;background:{p.canvas};color:{p.ink};font-family:'{dna.font_family}',sans-serif;display:grid;grid-template-rows:42px minmax(0,1fr) auto;overflow:hidden">
<header style="display:flex;align-items:start;justify-content:space-between"><span style="width:72px;height:5px;background:{p.accent}"></span>{logo}</header>
<main style="min-height:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center"><h1 style="max-width:1080px;font-size:{96 if len(title)<24 else 72}px;line-height:1.04;letter-spacing:-.035em;margin:0 0 20px;font-weight:900;color:{p.accent}">{_inline(title)}</h1><p style="font-size:28px;line-height:1.3;margin:0 0 22px;max-width:900px">{_inline(record.get('takeaway',''))}</p><div style="max-width:760px;font-size:20px;border-top:1px solid {p.accent};padding-top:18px">{copy}</div></main>
<footer style="font-size:14px;display:flex;justify-content:space-between;border-top:1px solid {p.accent};padding-top:12px"><span>{_inline(dna.subject[:80])}</span><span>{index+1:02d} / {total:02d}</span></footer></section>'''
    return {'html':editorial_frame(result,dna,index),'title':title,'slide_type':'content'}


def _original_table_copy(markdown: str, asset: dict) -> str | None:
    """Use a verified original table as the visible data, rather than duplicate it."""
    rows=[line for line in markdown.splitlines() if line.strip().startswith('|')]
    if not rows or not asset.get('data_preview'): return None
    normalize=lambda s:re.sub(r'\s+',' ',re.sub(r'[*_]','',s)).strip().casefold()
    # Match complete source cells; "38.3%" must not match "138.3%".
    source={normalize(cell) for line in asset['data_preview'].splitlines() for cell in line.split('|')}
    for row in rows:
        for cell in row.strip().strip('|').split('|'):
            if re.fullmatch(r'\s*:?-+:?\s*',cell): continue
            cell=normalize(cell)
            if cell and cell not in source: return None
    return '\n'.join(line for line in markdown.splitlines() if not line.strip().startswith('|'))


def _grouped_copy(record: dict, dna: PresentationDNA, assets: list[dict] | None = None) -> str | None:
    spec=record.get('layout_spec') or {}
    groups=spec.get('groups',[])
    if spec.get('kind') not in {'flow','comparison'} or not 2<=len(groups)<=4: return None
    lines=[re.sub(r'^[#*-]+\s+','',line.strip()) for line in record.get('content_markdown','').splitlines() if line.strip()]
    assigned=[i for group in groups for i in group.get('paragraph_indices',[])]+spec.get('shared_paragraph_indices',[])
    if any(type(i) is not int for i in assigned) or sorted(assigned)!=list(range(len(lines))): return None
    plain=re.sub(r'[*_]','', ' '.join(lines)).casefold()
    if any(not isinstance(group.get('label'),str) or group['label'].casefold() not in plain for group in groups): return None
    cards=[]
    p=dna.palette
    labels=[group['label'] for group in groups]
    supported_flow=spec['kind']=='flow' and bool(re.search(r'\s*→\s*'.join(re.escape(label) for label in labels),plain,re.I))
    from services.slide_subject_assets import mentions
    photos=[a for a in assets or [] if a.get('asset_role')=='subject_reference' and a.get('url')
            and a.get('image_kind')!='logo' and (a.get('selected') or a.get('provenance')=='web_search')]
    for group in groups:
        candidates=[a for a in assets or [] if a.get('asset_role')=='subject_reference'
                    and a.get('image_kind')=='photo' and a.get('url')
                    and mentions(group['label'],a.get('subject',''))]
        if not candidates: continue
        # Real product screens take priority over broad brand banners. An
        # explicitly requested, verified URL remains authoritative.
        photo=max(candidates,key=lambda a:(a['url'] in record.get('visual_instruction',''),
            bool(re.search(r'man-hinh|screen|phone|invest[-_]img|system|platform',a.get('label',''),re.I))))
        if photo['url'] not in {a['url'] for a in photos}: photos.append(photo)
    if spec['kind']=='comparison' and len(groups)==3 and len(record.get('content_markdown','').split())<=95:
        # The reference deck's audience page works because each real audience
        # photograph belongs to its own, explicitly labelled column. Never
        # distribute arbitrary pictures across comparison groups.
        used_urls=set(); triptych=[]
        for group in groups:
            match=next((a for a in assets or [] if a.get('asset_role')=='subject_reference'
                        and a.get('url') and a['url'] not in used_urls
                        and a.get('image_kind')!='logo'
                        and mentions(a.get('subject','')+' '+a.get('label',''),group['label'])),None)
            if match is None:break
            used_urls.add(match['url']);triptych.append(match)
        if len(triptych)==3 and all(sum(len(lines[i].split()) for i in group['paragraph_indices'])<=28
                                    for group in groups):
            cards=[]
            for group,photo in zip(groups,triptych):
                group_lines=[re.sub(r'^\*\*'+re.escape(group['label'])+r'\*\*:?\s*','',lines[i],flags=re.I)
                             for i in group['paragraph_indices']]
                group_copy=_copy('\n'.join(line for line in group_lines if line),size=18,gap=6)
                if group_copy is None:return None
                cards.append(f'<article style="min-width:0;background:{p.muted};border-top:4px solid {p.accent};padding:10px 12px 16px;display:flex;flex-direction:column;gap:12px"><div style="height:260px;overflow:hidden;border-radius:12px;background:{p.canvas}">{photo_frame(photo,"plain" if is_interface_asset(photo) else "clean_crop")}</div><h2 style="font-size:23px;line-height:1.15;margin:0">{_inline(group["label"])}</h2><div>{group_copy}</div></article>')
            summary=_copy(' '.join(lines[i] for i in sorted(set(spec.get('shared_paragraph_indices',[])))),size=18,gap=0)
            return '<div data-photo-triptych="true" style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px">'+''.join(cards)+'</div>'+(f'<div style="margin-top:14px;border-top:1px solid {p.accent};padding-top:10px">{summary}</div>' if summary else '')
    photos=photos[:2]
    image_led=bool(photos and len(record.get('content_markdown','').split())<=160)
    if photos and not image_led: return None  # do not shrink text to accommodate images
    shared=set(spec.get('shared_paragraph_indices',[]))
    if image_led and len(groups)==3:
        # A broad image sidebar and stacked reading path accommodate longer
        # paragraphs without turning product photographs into tiny thumbnails.
        steps=[]
        for i,group in enumerate(groups):
            copy=_copy('\n'.join(lines[j] for j in group['paragraph_indices']),size=20,gap=8)
            if copy is None: return None
            connector=f'<span aria-hidden="true" style="position:absolute;left:12px;top:32px;bottom:-4px;border-left:1px solid {p.accent}"><span style="position:absolute;bottom:-3px;left:-4px;border-left:3px solid transparent;border-right:3px solid transparent;border-top:5px solid {p.accent}"></span></span>' if supported_flow and i<len(groups)-1 else ''
            steps.append(f'<div style="position:relative;display:grid;grid-template-columns:34px minmax(0,1fr);gap:12px"><span style="font-size:20px;line-height:1.35;color:{p.accent};font-weight:800">{i+1:02d}</span><div>{copy}</div>{connector}</div>')
        summary=_copy(' '.join(lines[i] for i in sorted(shared)),size=18,gap=0) if shared else ''
        gallery=''.join(f'<figure style="margin:0;min-width:0"><img src="{html.escape(a["url"],quote=True)}" alt="{html.escape(a.get("label",""),quote=True)}" style="display:block;width:100%;height:{120 if i==0 and len(photos)==2 else 220}px;object-fit:contain"><figcaption style="font-size:12px;line-height:1.25;text-align:right">{_inline(a.get("subject",""))} · Minh họa sản phẩm — <a href="{html.escape(a.get("source_url",""),quote=True)}" style="color:inherit">{html.escape(urlparse(a.get("source_url","")).hostname or "Nguồn")}</a></figcaption></figure>' for i,a in enumerate(photos))
        return f'<div style="display:grid;grid-template-columns:minmax(0,1.8fr) minmax(0,1fr);gap:32px"><div style="display:grid;gap:10px;align-content:start">'+''.join(steps)+f'<div style="border-top:1px solid {p.accent};padding-top:10px">{summary}</div></div><aside style="display:grid;align-content:center;gap:20px;background:{p.muted};padding:12px">{gallery}</aside></div>'
    # The explicit paragraph assignment is authoritative. Arrow-bearing copy
    # may be a complete step, not shared prose; moving it emptied real cards.
    for index,group in enumerate(groups):
        copy=_copy('\n'.join(lines[i] for i in group['paragraph_indices'] if i not in shared),size=20,gap=8)
        if copy is None: return None
        arrow=''
        if supported_flow and index<len(groups)-1:
            arrow=f'<svg aria-hidden="true" viewBox="0 0 24 24" style="position:absolute;right:-24px;top:22px;width:24px;height:24px;color:{p.accent}"><path d="M2 12H21M15 6L21 12L15 18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        style=f'padding:10px 8px 0;border-top:2px solid {p.accent}' if image_led else f'background:{p.muted};padding:20px;border-top:4px solid {p.accent}'
        symbol=icon(subject_icons({'title':group['label'],'content_markdown':' '.join(lines[i] for i in group['paragraph_indices'])})[0],p.accent,28)
        cards.append(f'<div style="position:relative;min-width:0;{style}"><h2 style="display:flex;align-items:center;gap:10px;margin:0 0 12px;font-size:22px;line-height:1.25">{symbol}{_inline(group["label"])}</h2>{copy}{arrow}</div>')
    summary=_copy(' '.join(lines[i] for i in sorted(shared)),size=18,gap=6) if shared else ''
    hero=''
    if image_led:
        hero='<div style="display:grid;grid-template-columns:repeat('+str(len(photos))+',minmax(0,1fr));gap:32px;margin-bottom:14px">'+''.join(
            f'<figure style="margin:0;min-width:0;background:{p.muted};padding:6px 14px"><img src="{html.escape(a["url"],quote=True)}" alt="{html.escape(a.get("label",""),quote=True)}" style="display:block;width:100%;height:{132 if len(groups)==3 else 156}px;object-fit:contain"><figcaption style="font-size:12px;line-height:1.25"><span>{_inline(a.get("subject",""))} · Minh họa sản phẩm — </span><a href="{html.escape(a.get("source_url",""),quote=True)}" style="color:inherit">{html.escape(urlparse(a.get("source_url","")).hostname or "Nguồn")}</a></figcaption></figure>' for a in photos)+'</div>'
    return hero+f'<div style="display:grid;grid-template-columns:repeat({len(groups)},minmax(0,1fr));gap:24px;align-items:stretch">'+''.join(cards)+'</div>'+f'<div style="margin-top:14px;border-top:1px solid {p.accent};padding-top:10px">{summary}</div>'


def render_code_slide(record: dict, dna: PresentationDNA, assets: list[dict], index: int,
                      total: int, role: str = "content") -> dict | None:
    if record.get('renderer')=='designer':
        return None
    if any(a.get('asset_role')=='source_diagram' for a in assets):
        return None  # reconstruct the actual source relationships through the designer
    showcase = render_four_product_showcase(record, dna, assets, index, total, role)
    if (record.get('layout_spec') or {}).get('composition') == 'four_product_showcase':
        # An explicit art-direction decision must not silently degrade into
        # the generic two-photo/four-text-strip layout when an image is wrong.
        return showcase
    if showcase:
        return showcase
    choice = choose_layout(record, assets, index)
    if role=='title' and not any(a.get('asset_role')=='source_evidence' for a in assets):
        choice=LayoutChoice('cover','editorial_cover')
    if record.get('visual_form')=='chart' and not any(a.get('asset_role')=='source_evidence' for a in assets):
        return None  # a KPI numeral is not a substitute for the promised chart
    if choice.archetype not in dna.layouts:
        return None
    if choice.archetype=='cover' and role=='title':
        cover=_editorial_cover(record,dna,total,assets)
        if cover:
            cover['html']=_private_photo_credits(cover['html'],assets)
            cover['html']=editorial_frame(cover['html'],dna,index)
            return cover
    if choice.variant=='chapter_opener' and role=='content':
        return _chapter_opener(record,dna,assets,index,total)
    if choice.variant=='closing_statement' and role=='content':
        return _closing_statement(record,dna,assets,index,total)
    title = record.get("title", "")
    takeaway = record.get("takeaway", "")
    markdown = record.get("content_markdown", "")
    sources = [a for a in assets if a.get("asset_role") == "source_evidence" and a.get("url")]
    editable_tables = [a for a in assets if a.get('asset_role')=='source_table' and a.get('table_rows')]
    original_table = _original_table_copy(markdown,sources[0]) if len(sources)==1 else None
    visible_markdown = '\n'.join(line for line in markdown.splitlines() if not line.strip().startswith('|')) if editable_tables else original_table if original_table is not None else markdown
    # A measured, bounded subset: complex/dense slides retain the AI route.
    budget = 85 if sources else 220 if record.get('layout_spec') else 140
    if len(visible_markdown.split()) > (145 if original_table is not None else budget) or len(title) > 110 or len(takeaway) > 240:
        return None
    dense = len(visible_markdown.split()) > 100
    copy = _copy(visible_markdown, size=18 if role=='title' else 20 if dense else 22,
                 gap=6 if role=='title' else 8 if dense else 12)
    if copy is None and choice.archetype != "comparison" and not editable_tables:
        return None
    p = dna.palette
    brand_images = dna.brand_images
    if editable_tables:
        if len(editable_tables)!=1: return None
        asset=editable_tables[0];rows=asset['table_rows']
        interval=record.get('source_table_ranges',{}).get(asset.get('evidence_id'))
        if interval:
            start,end=interval
            if not 0<=start<end<=len(rows)-1:return None
            rows=[rows[0],*rows[1+start:1+end]]
        if not rows or len(rows)>10 or len(rows[0])>6 or any(len(r)!=len(rows[0]) for r in rows):return None
        # Tall cells must be paginated before design, never silently truncated.
        if sum(len(str(c).split()) for r in rows for c in r)>200:return None
        table='<table data-source-table="'+html.escape(str(asset.get('evidence_id','')))+'" style="width:100%;border-collapse:collapse;font-size:22px;line-height:1.35;table-layout:fixed">'
        for i,row in enumerate(rows):
            tag='th' if i==0 else 'td'
            table+='<tr>'+''.join(f'<{tag} style="padding:12px 14px;text-align:left;vertical-align:top;border-bottom:1px solid #DDE3E7;background:{p.ink if i==0 else p.muted if i%2 else p.canvas};color:{p.canvas if i==0 else p.ink};font-weight:{700 if i==0 else 400}">{html.escape(str(cell))}</{tag}>' for cell in row)+'</tr>'
        body=table+'</table>'
        non_table='\n'.join(line for line in markdown.splitlines() if not line.strip().startswith('|'))
        if non_table.strip():
            note=_copy(non_table,size=22,gap=6)
            if note is None or len(non_table.split())>70:return None
            body+=f'<div style="margin-top:16px;border-left:3px solid {p.accent};padding-left:14px">{note}</div>'
    elif sources:
        if len(sources) != 1 or len(visible_markdown.split()) > (145 if original_table is not None else 60):
            return None
        url = html.escape(sources[0]["url"], quote=True)
        if original_table is not None:
            lines=visible_markdown.splitlines()
            caveats=[line for line in lines if re.match(r'^\s*[-*]?\s*\*\*(?:Caveat|Lưu ý|Giới hạn)',line,re.I)]
            table_copy=_copy('\n'.join(line for line in lines if line not in caveats),size=18,gap=10)
            note=f'<div style="grid-column:1/-1;border-left:3px solid {p.accent};padding-left:12px">{_copy(chr(10).join(caveats),size=18,gap=0)}</div>' if caveats else ''
            body=f'<div style="display:grid;grid-template-columns:2.8fr 1fr;grid-template-rows:minmax(0,1fr) auto;gap:16px 28px;height:100%"><div style="min-height:0;background:white"><img src="{url}" alt="Original source table" style="width:100%;height:100%;object-fit:contain"></div><div>{table_copy}</div>{note}</div>'
        else:
            body = f'<div style="display:grid;grid-template-columns:2.2fr 1fr;gap:32px;height:100%"><div style="background:white;display:flex;align-items:center;justify-content:center"><img src="{url}" alt="Source evidence" style="width:100%;height:100%;object-fit:contain"></div><div>{copy}</div></div>'
    elif choice.variant == 'agenda':
        body=_agenda(markdown,dna)
        if body is None: return None
        photos=[a for a in assets if a.get('asset_role')=='subject_reference' and a.get('url') and a.get('image_kind')!='logo']
        if photos:
            photo=next((a for a in photos if a.get('selected')),photos[0])
            treatment=record.get('image_treatment','auto')
            body=f'<div style="display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:32px;height:100%;align-items:center"><div>{body}</div>{photo_frame(photo,"brush" if treatment=="auto" else treatment)}</div>'
    elif choice.variant == 'grouped_copy':
        body=_grouped_copy(record,dna,assets)
        if body is None: return None
    elif choice.archetype == "comparison":
        rows = [line.strip().strip("|").split("|") for line in markdown.splitlines() if line.strip().startswith("|")]
        if not rows or len(rows) > 10 or len(rows[0]) > 4:
            return None
        non_table = "\n".join(line for line in markdown.splitlines() if not line.strip().startswith("|"))
        if non_table.strip():
            return None  # never drop accompanying prose
        rows = [r for r in rows if not all(re.fullmatch(r"\s*:?-+:?\s*", c) for c in r)]
        if any(len(r) != len(rows[0]) for r in rows) or any(len(c) > 140 for r in rows for c in r):
            return None
        body = '<table style="width:100%;border-collapse:collapse;font-size:20px">' + ''.join(
            '<tr>' + ''.join(f'<{"th" if i == 0 else "td"} style="padding:12px;border:1px solid #DDE3E7;background:{p.ink if i == 0 else p.muted if i % 2 else p.canvas};color:{p.canvas if i == 0 else p.ink}">{_inline(c.strip())}</{"th" if i == 0 else "td"}>' for c in row) + '</tr>' for i,row in enumerate(rows)) + '</table>'
    elif choice.archetype == "diagram":
        from utils.smart_content_contract import explicit_slide_labels
        labels = explicit_slide_labels(record)
        plain = re.sub(r"[*_]", "", markdown)
        if not labels:
            chains = [re.sub(r'^[#*-]+\s+','',line).strip().split('→') for line in plain.splitlines() if '→' in line]
            labels = next(([part.strip() for part in chain] for chain in chains
                           if 3 <= len(chain) <= 4 and all(2 <= len(part.strip()) <= 60 for part in chain)), [])
        if (not 3 <= len(labels) <= 4 or len(markdown.split()) > 95
                or not re.search(r"\s*→\s*".join(re.escape(label) for label in labels), plain, re.I)):
            return None  # do not replace a promised diagram with plain prose
        nodes = []
        for i, label in enumerate(labels):
            arrow = '<span aria-hidden="true">→</span>' if i < len(labels)-1 else ''
            nodes.append(f'<div style="display:flex;align-items:center;gap:14px;flex:1;min-width:0"><div style="border:1px solid {p.accent};border-radius:16px;background:{p.muted};padding:24px 18px;width:100%;font-size:22px;font-weight:700"><div style="font-size:14px;color:{p.accent};margin-bottom:12px">{i+1:02d}</div>{_inline(label)}</div>{arrow}</div>')
        nodes = ''.join(nodes)
        # Only linear relationships explicitly supplied by the author are connected.
        if labels:
            body = f'<div style="display:flex;gap:12px;margin-bottom:28px">{nodes}</div><div>{copy}</div>'
    elif choice.archetype == "cover":
        if markdown.count('\n') >= 10: copy = _columns(copy)
        if brand_images:
            image = brand_images[0]
            brand_mark = f'<figure style="margin:0;height:100%"><img src="{html.escape(image.url,quote=True)}" alt="{html.escape(image.label,quote=True)}" style="width:100%;height:calc(100% - 24px);object-fit:contain">{_image_credit(image.source_url)}</figure>'
            ratio = '1.8fr 1fr' if markdown.count('\n') >= 10 else '1fr 1.2fr'
            body = f'<div style="display:grid;grid-template-columns:{ratio};gap:36px;height:100%;align-items:center"><div style="border-left:6px solid {p.accent};padding-left:24px">{copy}</div>{brand_mark}</div>'
        elif dna.logo_enabled and dna.logo_url:
            brand_mark = f'<img src="{html.escape(dna.logo_url,quote=True)}" alt="Brand identity" style="width:360px;height:140px;object-fit:contain">'
            body = f'<div style="display:grid;grid-template-columns:1.4fr 1fr;gap:48px;align-items:center"><div style="border-left:6px solid {p.accent};padding-left:28px">{copy}</div>{brand_mark}</div>'
        else:
            # A decorative brand panel, never a simulated chart or unsupported image.
            panel = f'<div aria-hidden="true" style="height:100%;min-height:220px;border-radius:2px;background:repeating-linear-gradient(125deg,transparent 0 38px,{p.canvas}22 39px 41px,transparent 42px 80px),linear-gradient(135deg,{p.ink},{p.accent});position:relative;overflow:hidden"><div style="position:absolute;inset:25% -20% -60% 25%;border:2px solid {p.canvas}66;transform:rotate(-25deg)"></div></div>'
            body = f'<div style="display:grid;grid-template-columns:1.4fr 1fr;gap:48px;height:100%;align-items:center"><div style="border-left:6px solid {p.accent};padding-left:28px">{copy}</div>{panel}</div>'
    elif choice.archetype == "kpi":
        metric = re.search(r"\d[\d.,]*\s*(?:%|triệu|tỷ|million|billion)", markdown)
        body = f'<div style="display:grid;grid-template-columns:1fr 1.8fr;gap:40px"><div style="font-size:72px;line-height:1.1;font-weight:800;color:{p.accent}">{html.escape(metric.group())}</div><div>{copy}</div></div>'
    else:
        photos=[a for a in assets if a.get('asset_role')=='subject_reference' and a.get('url') and a.get('image_kind')!='logo']
        if choice.variant == 'photo_split':
            # A brand-library image can belong to another product or section.
            # Use a slide-scoped photo, then draw a subject illustration.
            photo=next((a for a in photos if a.get('selected')),photos[0] if photos else None)
            if not photo and subject_icons(record)==['layers','target','globe']:
                return None  # an unfamiliar subject needs a real tailored SVG drawing, not generic icons
            treatment=record.get('image_treatment','auto')
            # The reference image demo shows that crop, edge treatment and
            # shadow should serve the photo. Avoid cycling decorative masks by
            # slide number: a calm rounded frame is the body-slide default;
            # explicit editorial treatments remain available in the storyboard.
            if treatment=='auto':treatment='rounded'
            visual=photo_frame(photo,treatment) if photo else illustration_panel(record,dna,index)
            if photo and treatment=='rounded':
                # A low-contrast offset panel gives the photo a deliberate
                # printed-card treatment without placing decoration over it.
                visual=(f'<div data-photo-stage="rounded" style="position:relative;'
                        'height:100%;min-height:0">'
                        f'<div aria-hidden="true" style="position:absolute;inset:18px 0 0 18px;'
                        f'border:1px solid {p.accent};border-radius:20px;background:{p.muted}"></div>'
                        f'<div style="position:absolute;inset:0 18px 18px 0">{visual}</div></div>')
            short=len(markdown.split())<=50
            text_style=f'background:{p.muted};padding:28px;border-left:5px solid {p.accent};display:flex;flex-direction:column;justify-content:center;' if short else 'align-self:center;'
            if short:copy=copy.replace('font-size:22px','font-size:24px')
            body=f'<div style="display:grid;grid-template-columns:minmax(0,.85fr) minmax(0,1.15fr);gap:28px;height:100%;align-items:stretch"><div style="{text_style}">{copy}</div>{visual}</div>'
        else:
            body = _columns(copy) if choice.variant == 'split' else f'<div style="max-width:1100px">{copy}</div>'
    logo = f'<img src="{html.escape(dna.logo_url,quote=True)}" alt="Brand logo" style="width:110px;height:32px;object-fit:contain">' if dna.logo_enabled and dna.logo_url else ''
    evidence = html.escape(" ".join(record.get("source_evidence_ids", [])), quote=True)
    section = _inline(f"{record.get('section_id','')} {record.get('section_title','')}").strip()
    if section: section = f'<div style="display:flex;align-items:center;gap:10px;font-size:14px;color:{p.accent};font-weight:700;margin-bottom:8px">{icon(subject_icons(record)[0],p.accent,22)}{section}</div>'
    result = f'''<section data-slide-type="{role}" data-slide-title="{html.escape(title,quote=True)}" data-source-evidence="{evidence}" data-layout-archetype="{choice.archetype}" data-dna-hash="{dna.fingerprint()}" style="width:1280px;height:720px;box-sizing:border-box;padding:{dna.safe_margin}px;background:{p.canvas};color:{p.ink};font-family:'{dna.font_family}',sans-serif;display:grid;grid-template-rows:auto 1fr auto;gap:24px;overflow:hidden">
<header><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><span style="width:48px;height:5px;background:{p.accent}"></span>{logo}</div>{section}<h1 style="font-size:{54 if role == 'title' else 34 if len(title)>80 else 38}px;line-height:1.15;margin:0 0 16px;font-weight:800">{_inline(title)}</h1><p style="font-size:{20 if len(takeaway)>140 else 22}px;line-height:1.35;margin:0">{_inline(takeaway)}</p></header>
<div style="min-height:0">{body}</div><footer style="border-top:1px solid #DDE3E7;padding-top:12px;display:flex;justify-content:space-between;font-size:14px"><span>{html.escape(dna.subject[:90])}</span><span>{index+1:02d} / {total:02d}</span></footer></section>'''
    result = result.replace('<section ', '<section class="relative h-[720px] w-[1280px] overflow-hidden" ',1)
    if role == 'content':
        # Keep the original evidence large; the generic editorial header consumed
        # most of the canvas and made a perfectly loaded source table unreadable.
        compact_header=f'<header><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">{section}{logo}</div><h1 style="font-size:34px;line-height:1.15;margin:0 0 8px;font-weight:800">{_inline(title)}</h1><p style="font-size:22px;line-height:1.3;margin:0">{_inline(takeaway)}</p></header>'
        result=re.sub(r'<header>.*?</header>',lambda _:compact_header,result,flags=re.S)
        result=result.replace('grid-template-rows:auto 1fr auto;gap:24px;','grid-template-rows:auto 1fr auto;gap:16px;',1)
        if original_table is not None:
            result=result.replace(f'padding:{dna.safe_margin}px;',f'padding:{min(dna.safe_margin,40)}px;',1)
    if any(a.get('selected') and a.get('url') not in html.unescape(result) for a in assets):
        return None  # designer must incorporate an explicit user-selected image
    return {"html": editorial_frame(_private_photo_credits(result,assets),dna,index), "title": title, "slide_type": role}


def _fallback_markdown_copy(markdown: str, size: int) -> str:
    """Render plain approved copy without dropping any non-table line."""
    lines = []
    for raw in (markdown or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("|") or re.fullmatch(r"[-:| ]+", line):
            continue
        line = re.sub(r"^[#*-]+\s*", "", line)
        lines.append(line)
    return "".join(
        f'<p style="margin:0 0 8px;font-size:{size}px;line-height:1.3">{_inline(line)}</p>'
        for line in lines
    )


def _fallback_table(record: dict, assets: list[dict], dna: PresentationDNA) -> str:
    rows = []
    evidence_id = ""
    source_tables = [asset for asset in assets
                     if asset.get("asset_role") == "source_table"
                     and asset.get("table_rows")]
    if len(source_tables) > 1:
        tables = [
            _fallback_table(record, [{**asset, "_fallback_compact": True}], dna)
            for asset in source_tables
        ]
        return (f'<div data-multi-source-tables="true" style="display:grid;'
                f'grid-template-columns:repeat({min(2, len(tables))},minmax(0,1fr));'
                f'gap:10px;align-content:start">{"".join(tables)}</div>')
    source_table = source_tables[0] if source_tables else None
    if source_table:
        rows = source_table["table_rows"]
        evidence_id = str(source_table.get("evidence_id", ""))
        interval = (record.get("source_table_ranges") or {}).get(evidence_id)
        if interval and rows:
            start, end = interval
            rows = [rows[0], *rows[1 + start:1 + end]]
    if not rows:
        rows = [line.strip().strip("|").split("|") for line in
                (record.get("content_markdown") or "").splitlines()
                if line.strip().startswith("|")]
        rows = [row for row in rows if not all(
            re.fullmatch(r"\s*:?-+:?\s*", cell) for cell in row)]
    if not rows or len(rows[0]) < 2 or any(len(row) != len(rows[0]) for row in rows):
        return ""
    columns = len(rows[0])
    cell_words = sum(len(str(cell).split()) for row in rows for cell in row)
    font_size = (12 if cell_words > 180 else 14 if cell_words > 120 else
                 17 if columns <= 4 else 14 if columns <= 6 else 12)
    padding = ("6px 7px" if cell_words > 120 else
               "10px 11px" if columns <= 4 else "8px 7px")
    if source_table and source_table.get("_fallback_compact"):
        font_size = 12
        padding = "3px 4px"
    p = dna.palette
    body = [f'<table data-source-table="{html.escape(evidence_id, quote=True)}" '
            f'style="width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed;'
            f'font-size:{font_size}px;line-height:1.24;border:1px solid #DDE3E7;border-radius:14px;overflow:hidden">']
    for row_index, row in enumerate(rows):
        tag = "th" if row_index == 0 else "td"
        cells = []
        for column_index, cell in enumerate(row):
            highlighted = column_index == 1 and columns >= 4
            background = (p.accent if row_index == 0 and highlighted else
                          p.ink if row_index == 0 else
                          f"{p.accent}12" if highlighted else
                          p.muted if row_index % 2 else p.canvas)
            color = p.canvas if row_index == 0 else p.accent if highlighted else p.ink
            cells.append(
                f'<{tag} style="padding:{padding};text-align:left;vertical-align:top;'
                f'border-right:1px solid #DDE3E7;border-bottom:1px solid #DDE3E7;'
                f'background:{background};color:{color};font-weight:{800 if row_index == 0 or highlighted else 500}">'
                f'{_inline(str(cell).strip())}</{tag}>'
            )
        body.append("<tr>" + "".join(cells) + "</tr>")
    body.append("</table>")
    return "".join(body)


def render_code_fallback_slide(record: dict, dna: PresentationDNA, assets: list[dict],
                               index: int, total: int, role: str = "content") -> dict:
    """Deterministic last-resort layout used when the configured AI is unavailable.

    It preserves approved copy and assigned assets. The regular AI designer is
    still preferred for complex compositions; this path prevents a provider
    outage from leaving a deck stuck or blank.
    """
    title = str(record.get("title") or f"Slide {index + 1}")
    takeaway = str(record.get("takeaway") or "")
    normalize_heading = lambda value: re.sub(r"\W+", " ", value, flags=re.UNICODE).strip().casefold()
    visible_takeaway = "" if normalize_heading(takeaway) == normalize_heading(title) else takeaway
    markdown = str(record.get("content_markdown") or "")
    p = dna.palette
    words = len(markdown.split())
    copy_size = 18 if words <= 80 else 15 if words <= 130 else 13
    copy = _fallback_markdown_copy(markdown, copy_size)
    table = _fallback_table(record, assets, dna)
    required_visuals = [asset for asset in assets if asset.get("url") and
                        asset.get("asset_role") in {"source_evidence", "source_diagram"}]
    photos = [asset for asset in assets if asset.get("url") and
              asset.get("asset_role") == "subject_reference" and
              asset.get("image_kind") != "logo"]
    selected = [asset for asset in photos if asset.get("selected")]
    photos = selected or photos[:1]

    if table:
        body = table
        multi_table = 'data-multi-source-tables="true"' in table
        prose = _fallback_markdown_copy("\n".join(
            line for line in markdown.splitlines() if not line.strip().startswith("|")),
            12 if multi_table else 13 if words > 120 else 16,
        )
        if multi_table:
            prose = prose.replace("margin:0 0 8px", "margin:0 0 3px")
        if prose:
            body += (f'<div style="margin-top:{4 if multi_table else 12}px;'
                     f'border-left:3px solid {p.accent};padding:{5 if multi_table else 10}px '
                     f'{8 if multi_table else 14}px;background:{p.muted}">{prose}</div>')
    elif required_visuals:
        gallery = "".join(
            f'<figure style="margin:0;min-width:0;height:100%;background:{p.canvas};padding:8px;'
            f'border:1px solid #DDE3E7;border-radius:16px"><img src="{html.escape(asset["url"], quote=True)}" '
            f'alt="{html.escape(asset.get("label", "Source visual"), quote=True)}" '
            'style="width:100%;height:100%;object-fit:contain"></figure>'
            for asset in required_visuals
        )
        body = (f'<div style="display:grid;grid-template-columns:minmax(0,1.65fr) minmax(0,1fr);'
                f'gap:24px;height:100%"><div style="display:grid;grid-template-columns:repeat('
                f'{len(required_visuals)},minmax(0,1fr));gap:12px;min-height:0">{gallery}</div>'
                f'<aside style="align-self:center;border-left:4px solid {p.accent};padding-left:18px">'
                f'{copy}</aside></div>')
    elif photos:
        gallery = "".join(photo_frame(asset, record.get("image_treatment") or "rounded")
                          for asset in photos)
        body = (f'<div style="display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);'
                f'gap:28px;height:100%;align-items:stretch"><div style="align-self:center;'
                f'background:{p.muted};border-left:5px solid {p.accent};padding:24px">{copy}</div>'
                f'<div style="display:grid;grid-template-columns:repeat({len(photos)},minmax(0,1fr));'
                f'gap:12px;min-height:0">{gallery}</div></div>')
    elif record.get("visual_form") in {"diagram", "process", "timeline", "comparison"}:
        blocks = [re.sub(r"^[#*-]+\s*", "", line.strip()) for line in markdown.splitlines()
                  if line.strip() and not line.strip().startswith("|")]
        if len(blocks) > 6:
            blocks = blocks[:5] + [" ".join(blocks[5:])]
        cards = []
        diagram_size = 13 if words > 120 else 14 if len(blocks) >= 5 else min(copy_size, 16)
        for card_index, block in enumerate(blocks or [takeaway]):
            symbol = icon(subject_icons({"title": block, "content_markdown": block})[0], p.accent, 26)
            cards.append(
                f'<article style="min-width:0;background:{p.muted};border-top:3px solid {p.accent};'
                f'border-radius:0 0 12px 12px;padding:10px 12px;display:grid;grid-template-columns:30px 1fr;'
                f'gap:8px;align-content:start">{symbol}<div style="font-size:{diagram_size}px;line-height:1.22">'
                f'{_inline(block)}</div></article>'
            )
        columns = 3 if len(cards) >= 5 else 2
        body = (f'<div style="display:grid;grid-template-columns:repeat({columns},minmax(0,1fr));'
                f'gap:10px;align-content:stretch;height:100%">{"".join(cards)}</div>')
    else:
        visual = illustration_panel(record, dna, index)
        body = (f'<div style="display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr);'
                f'gap:28px;height:100%;align-items:stretch"><div style="align-self:center">{copy}</div>'
                f'<div style="min-height:0">{visual}</div></div>')

    logo = (f'<img src="{html.escape(dna.logo_url, quote=True)}" alt="Brand logo" '
            'style="width:120px;height:34px;object-fit:contain">') if dna.logo_enabled and dna.logo_url else ""
    section = _inline(f"{record.get('section_id', '')} {record.get('section_title', '')}".strip())
    evidence = html.escape(" ".join(record.get("source_evidence_ids", [])), quote=True)
    dense_multi_table = bool(table and 'data-multi-source-tables="true"' in table)
    safe_margin = min(dna.safe_margin, 32) if dense_multi_table else dna.safe_margin
    heading_size = 26 if dense_multi_table else 30 if len(title) > 80 else 36
    result = f'''<section data-code-fallback="true" data-slide-type="{role}" data-slide-title="{html.escape(title, quote=True)}" data-source-evidence="{evidence}" data-layout-archetype="fallback" data-dna-hash="{dna.fingerprint()}" style="width:1280px;height:720px;box-sizing:border-box;padding:{safe_margin}px;background:{p.canvas};color:{p.ink};font-family:'{dna.font_family}',sans-serif;display:grid;grid-template-rows:auto minmax(0,1fr) auto;gap:{8 if dense_multi_table else 12}px;overflow:hidden">
<header><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:{4 if dense_multi_table else 7}px"><span style="font-size:{12 if dense_multi_table else 13}px;font-weight:800;color:{p.accent}">{section}</span>{logo}</div><h1 style="font-size:{heading_size}px;line-height:1.1;margin:0 0 {4 if visible_takeaway and dense_multi_table else 6 if visible_takeaway else 0}px;font-weight:850">{_inline(title)}</h1>{f'<p style="font-size:{14 if dense_multi_table else 17}px;line-height:1.2;margin:0;color:{p.ink}CC">{_inline(visible_takeaway)}</p>' if visible_takeaway else ''}</header>
<main style="min-height:0">{body}</main><footer style="border-top:1px solid #DDE3E7;padding-top:9px;display:flex;justify-content:space-between;font-size:13px"><span>{html.escape(dna.subject[:90])}</span><span>{index + 1:02d} / {total:02d}</span></footer></section>'''
    return {"html": editorial_frame(_private_photo_credits(result, assets), dna, index),
            "title": title, "slide_type": role}
