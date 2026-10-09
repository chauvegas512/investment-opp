"""A bounded, image-led layout for four named products or subjects.

The layout only compiles when each group has its own relevant image. A weak
image search result is not enough to claim that a generic photograph depicts a
specific product; those slides stay on the designer route.
"""
from __future__ import annotations

import html
import re
import unicodedata

from services.presentation_dna import PresentationDNA


_GENERIC = {
    'the', 'tin', 'dung', 'card', 'credit', 'visa', 'techcombank',
    'product', 'san', 'pham', 'ngan', 'hang', 'bank', 'theo', 'cho',
}


def _tokens(value: str) -> set[str]:
    value = ''.join(ch for ch in unicodedata.normalize('NFD', value.casefold())
                    if unicodedata.category(ch) != 'Mn').replace('đ', 'd')
    return {part for part in re.findall(r'[a-z0-9]+', value)
            if len(part) >= 3 and part not in _GENERIC}


def _colors(label: str, fallback: str) -> tuple[str, str]:
    words = _tokens(label)
    if words & {'eco', 'green', 'esg', 'xanh', 'sustainable'}:
        return '#EAF5ED', '#26804B'
    if words & {'airlines', 'airline', 'flight', 'travel', 'bay', 'hangkhong'}:
        return '#EAF2FA', '#27649A'
    if words & {'everyday', 'shopping', 'daily', 'mua', 'sam'}:
        return '#FFF3E5', '#A85B00'
    if words & {'signature', 'premium', 'luxury', 'priority'}:
        return '#F5F1E9', '#A47C40'
    return '#F2F5F5', fallback


def _group_copy(label: str, lines: list[str], indices: list[int]) -> str:
    parts = []
    for index in indices:
        value = lines[index]
        value = re.sub(r'^[#*\-]+\s*', '', value)
        value = re.sub(r'^\*{0,2}' + re.escape(label) + r'\*{0,2}\s*[:：—–-]?\s*', '', value, flags=re.I)
        value = re.sub(r'[*_`]+', '', value).strip()
        if value:
            parts.append(value)
    return ' '.join(parts)


def _assign_images(groups: list[dict], assets: list[dict]) -> list[dict] | None:
    names = [str(group.get('label', '')) for group in groups]
    common = set.intersection(*(_tokens(name) for name in names)) if names else set()
    photos = [asset for asset in assets if asset.get('asset_role') in {'subject_reference', 'decorative_web'}
              and asset.get('url') and asset.get('image_kind') != 'logo']
    ranked = []
    for index, name in enumerate(names):
        distinctive = _tokens(name) - common
        if not distinctive:
            return None
        pinned = [asset for asset in photos if asset.get('selected')
                  and asset.get('image_need_id') == f'group-{index + 1}']
        if pinned:
            ranked.append([(100, asset) for asset in pinned])
            continue
        options = []
        for asset in photos:
            # A search query/subject is only the intent; the result's own label
            # or source path must also identify this particular item.
            evidence = _tokens(' '.join(str(asset.get(key, '')) for key in ('label', 'source_url', 'original_url')))
            if str(asset.get('url', '')).startswith('https://'):
                evidence |= _tokens(asset['url'])
            hits = len(distinctive & evidence)
            if not hits:
                continue
            score = hits * 10 + int(asset.get('selected', False)) * 5
            score += int(asset.get('provenance') == 'official_website') * 3
            score += int(bool(distinctive & _tokens(str(asset.get('label', ''))))) * 2
            options.append((score, asset))
        if not options:
            return None
        ranked.append(sorted(options, key=lambda item: (-item[0], item[1]['url'])))

    best: tuple[int, list[dict]] | None = None
    def visit(index: int, used: set[str], score: int, chosen: list[dict]) -> None:
        nonlocal best
        if index == len(ranked):
            if best is None or score > best[0]:
                best = (score, chosen.copy())
            return
        for points, asset in ranked[index]:
            fingerprint = asset.get('image_fingerprint') or asset['url']
            if fingerprint in used:
                continue
            used.add(fingerprint); chosen.append(asset)
            visit(index + 1, used, score + points, chosen)
            chosen.pop(); used.remove(fingerprint)
    visit(0, set(), 0, [])
    return best[1] if best else None


def render_four_product_showcase(record: dict, dna: PresentationDNA, assets: list[dict],
                                 index: int, total: int, role: str) -> dict | None:
    spec = record.get('layout_spec') or {}
    groups = spec.get('groups') or []
    if (role != 'content' or spec.get('kind') != 'comparison'
            or spec.get('composition') != 'four_product_showcase' or len(groups) != 4
            or record.get('visual_form') not in {'comparison', 'photo'}
            or any(asset.get('asset_role') in {'source_evidence', 'source_table', 'source_diagram'} for asset in assets)):
        return None
    markdown = str(record.get('content_markdown', ''))
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    assigned = [i for group in groups for i in group.get('paragraph_indices', [])]
    shared = spec.get('shared_paragraph_indices', [])
    if (not lines or any(type(i) is not int for i in assigned + shared)
            or sorted(assigned + shared) != list(range(len(lines)))):
        return None
    title = str(record.get('title', ''))
    takeaway = str(record.get('takeaway', ''))
    if len(title) > 78 or len(takeaway) > 125:
        return None
    images = _assign_images(groups, assets)
    if images is None:
        return None
    if any(asset.get('selected') and asset.get('url') not in {item['url'] for item in images}
           for asset in assets if asset.get('asset_role') in {'subject_reference', 'decorative_web'}):
        return None
    descriptions = [_group_copy(group['label'], lines, group['paragraph_indices']) for group in groups]
    if any(not value or len(value.split()) > 26 for value in descriptions):
        return None
    shared_copy = ' '.join(re.sub(r'[*_`]+', '', lines[i]) for i in shared).strip()
    if len(shared_copy.split()) > 18:
        return None
    p = dna.palette
    tiles = []
    for order, (group, asset, description) in enumerate(zip(groups, images, descriptions), 1):
        fill, accent = _colors(group['label'] + ' ' + description, p.accent)
        image_url = html.escape(str(asset['url']), quote=True)
        label = html.escape(str(group['label']))
        copy = html.escape(description)
        tiles.append(f'''<article data-showcase-item="{order}" style="min-width:0;min-height:0;display:grid;grid-template-columns:45% minmax(0,55%);overflow:hidden;border:1px solid #DEE4E7;border-radius:18px;background:{fill};box-shadow:0 5px 16px rgba(21,28,33,.09)">
<div style="min-width:0;min-height:0;padding:12px;background:linear-gradient(145deg,{fill},#FFFFFF);display:flex;align-items:center;justify-content:center"><img src="{image_url}" alt="{label}" style="display:block;width:100%;height:100%;object-fit:contain"></div>
<div style="min-width:0;box-sizing:border-box;padding:22px 22px 16px 20px;display:flex;flex-direction:column;justify-content:center;border-left:3px solid {accent}88"><div style="font-size:12px;letter-spacing:.12em;font-weight:800;color:{accent};margin-bottom:13px">{order:02d} / 04</div><h2 style="font-size:{24 if len(label)<30 else 21}px;line-height:1.12;letter-spacing:-.025em;margin:0 0 15px;font-weight:800">{label}</h2><div aria-hidden="true" style="width:60px;height:3px;background:{accent};margin-bottom:13px"></div><p style="font-size:17px;line-height:1.27;margin:0;color:{p.ink}">{copy}</p></div></article>''')
    logo = (f'<img src="{html.escape(dna.logo_url,quote=True)}" alt="Brand logo" style="width:140px;height:30px;object-fit:contain">'
            if dna.logo_enabled and dna.logo_url else '')
    footer = (f'<div style="font-size:15px;line-height:1.25">'
              f'{html.escape(shared_copy)}</div>') if shared_copy else ''
    evidence = html.escape(' '.join(record.get('source_evidence_ids', [])), quote=True)
    result = f'''<section class="relative h-[720px] w-[1280px] overflow-hidden" data-slide-type="content" data-slide-title="{html.escape(title,quote=True)}" data-layout-archetype="comparison" data-layout-variant="four_product_showcase" data-source-evidence="{evidence}" data-dna-hash="{dna.fingerprint()}" style="width:1280px;height:720px;box-sizing:border-box;padding:24px 42px 26px;background:{p.canvas};color:{p.ink};font-family:'{dna.font_family}',sans-serif;overflow:hidden">
<header style="display:flex;align-items:center;justify-content:space-between;height:30px"><span style="font-size:13px;letter-spacing:.12em;font-weight:800;color:{p.accent}">{html.escape(dna.subject[:65])}</span>{logo}</header>
<h1 style="font-size:{37 if len(title)<58 else 33}px;line-height:1.08;margin:8px 0 5px;font-weight:800;letter-spacing:-.025em">{html.escape(title)}</h1>
<p style="font-size:18px;line-height:1.25;color:{p.ink};opacity:.75;margin:0">{html.escape(takeaway)}</p>
<main data-showcase-grid="true" style="margin-top:17px;height:{514 if not shared_copy and len(title)<58 else 474 if not shared_copy else 454}px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:repeat(2,minmax(0,1fr));gap:16px">{''.join(tiles)}</main>
<footer style="margin-top:10px;padding-top:7px;border-top:1px solid {p.accent};display:flex;align-items:end;justify-content:space-between;gap:18px;min-height:20px"><div style="flex:1">{footer}</div><span style="font-size:12px;white-space:nowrap;color:{p.accent}">{index+1:02d} / {total:02d}</span></footer></section>'''
    return {'html': result, 'title': title, 'slide_type': 'content'}
