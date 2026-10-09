"""Versioned, reviewable design contracts shared by all Smart slide renderers."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class BrandEvidence(BaseModel):
    source_url: str = Field(max_length=2048)
    kind: Literal["color", "font", "logo", "website", "image"]
    value: str = Field(max_length=2048)
    method: Literal["source_text", "website_html", "website_css", "website_image", "user"]


class BrandImage(BaseModel):
    url: str = Field(max_length=2048)
    source_url: str = Field(max_length=2048)
    label: str = Field(max_length=320)


class DesignPalette(BaseModel):
    canvas: str = Field(default="#FFFFFF", pattern=r"^#[0-9a-fA-F]{6}$")
    ink: str = Field(default="#17232B", pattern=r"^#[0-9a-fA-F]{6}$")
    accent: str = Field(default="#126B8A", pattern=r"^#[0-9a-fA-F]{6}$")
    muted: str = Field(default="#F0F3F5", pattern=r"^#[0-9a-fA-F]{6}$")


class VisualEvidenceTiers(BaseModel):
    """Separate observed facts from interpretation and safe design defaults."""
    confirmed: list[str] = Field(default_factory=list, max_length=24)
    inferred: list[str] = Field(default_factory=list, max_length=24)
    defaults: list[str] = Field(default_factory=list, max_length=24)


class BrandPersonality(BaseModel):
    keywords: list[str] = Field(default_factory=list, max_length=8)
    explanation: str = Field(default="", max_length=800)


class TypographyDNA(BaseModel):
    heading: str = Field(default="Be Vietnam Pro", max_length=80)
    body: str = Field(default="Be Vietnam Pro", max_length=80)
    rules: list[str] = Field(default_factory=list, max_length=12)


class ShapeLanguage(BaseModel):
    geometry: str = Field(default="Rectangular editorial grid", max_length=240)
    radius: str = Field(default="Moderate", max_length=120)
    border: str = Field(default="Thin neutral dividers", max_length=240)
    shadow: str = Field(default="Restrained or none", max_length=240)


class LayoutLanguage(BaseModel):
    density: str = Field(default="Balanced", max_length=160)
    alignment: str = Field(default="Strong left alignment", max_length=240)
    whitespace: str = Field(default="Generous safe margins", max_length=240)
    preferred_patterns: list[str] = Field(default_factory=list, max_length=16)


class IconographyDNA(BaseModel):
    style: str = Field(default="Simple outline icons", max_length=240)
    rules: list[str] = Field(default_factory=list, max_length=12)


class PhotographyDNA(BaseModel):
    style: str = Field(default="Relevant editorial photography", max_length=240)
    prefer: list[str] = Field(default_factory=list, max_length=12)
    avoid: list[str] = Field(default_factory=list, max_length=12)


class DiagramLanguage(BaseModel):
    node_style: str = Field(default="Clear labeled nodes", max_length=240)
    connector_style: str = Field(default="Directional connectors with restrained arrowheads", max_length=240)
    rules: list[str] = Field(default_factory=list, max_length=12)


class DataVisualizationDNA(BaseModel):
    chart_style: str = Field(default="Evidence-first, direct labels", max_length=240)
    rules: list[str] = Field(default_factory=list, max_length=12)


class SemanticGraphDNA(BaseModel):
    structure: str = Field(default="", max_length=320)
    nodes: list[str] = Field(default_factory=list, max_length=24)
    edges: list[str] = Field(default_factory=list, max_length=32)
    cross_cutting: list[str] = Field(default_factory=list, max_length=16)


class SlideArchetypeDNA(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    when_to_use: str = Field(default="", max_length=320)
    composition: str = Field(default="", max_length=500)


class DeckContractDNA(BaseModel):
    locked: list[str] = Field(default_factory=list, max_length=24)
    flexible: list[str] = Field(default_factory=list, max_length=24)


class PresentationDNA(BaseModel):
    version: Literal["1.0", "2.0"] = "2.0"
    name: str = Field(default="Source-derived editorial", min_length=1, max_length=180)
    subject: str = Field(default="", max_length=180)
    brand_mode: Literal["inspired", "neutral"] = "neutral"
    palette: DesignPalette = Field(default_factory=DesignPalette)
    font_family: str = Field(default="Be Vietnam Pro", pattern=r"^[\w .,-]{1,80}$")
    direction: str = Field(default="Light editorial, strong hierarchy, restrained accents", max_length=2400)
    logo_url: str = Field(default="", max_length=2048, pattern=r"^(https://[^\s<>\"']+|/app_data/images/[^\s<>\"']+)?$")
    logo_enabled: bool = False
    safe_margin: int = Field(default=56, ge=48, le=72)
    layouts: list[Literal["cover", "source_visual", "comparison", "kpi", "diagram", "editorial"]] = Field(
        default_factory=lambda: ["cover", "source_visual", "comparison", "kpi", "diagram", "editorial"], min_length=1, max_length=6)
    evidence: list[BrandEvidence] = Field(default_factory=list, max_length=40)
    evidence_tiers: VisualEvidenceTiers = Field(default_factory=VisualEvidenceTiers)
    brand_personality: BrandPersonality = Field(default_factory=BrandPersonality)
    typography: TypographyDNA = Field(default_factory=TypographyDNA)
    shape_language: ShapeLanguage = Field(default_factory=ShapeLanguage)
    layout_language: LayoutLanguage = Field(default_factory=LayoutLanguage)
    iconography: IconographyDNA = Field(default_factory=IconographyDNA)
    photography: PhotographyDNA = Field(default_factory=PhotographyDNA)
    diagram_language: DiagramLanguage = Field(default_factory=DiagramLanguage)
    data_visualization: DataVisualizationDNA = Field(default_factory=DataVisualizationDNA)
    visual_grammar: list[str] = Field(default_factory=list, max_length=24)
    anti_dna: list[str] = Field(default_factory=list, max_length=24)
    semantic_graph: SemanticGraphDNA = Field(default_factory=SemanticGraphDNA)
    slide_archetypes: list[SlideArchetypeDNA] = Field(default_factory=list, max_length=16)
    deck_contract: DeckContractDNA = Field(default_factory=DeckContractDNA)
    image_prompt: str = Field(default="", max_length=2400)
    approved: bool = False
    brand_images: list[BrandImage] = Field(default_factory=list, max_length=4)

    @field_validator("logo_url")
    @classmethod
    def public_logo_url(cls, value: str) -> str:
        if value and not value.startswith('/app_data/images/'):
            from services.brand_discovery import public_https_url
            public_https_url(value)
        return value

    def fingerprint(self) -> str:
        payload = self.model_dump(exclude={"approved"}, mode="json")
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def to_prompt(self) -> str:
        return "APPROVED PRESENTATION DNA (overrides provisional art direction, palette and logo prohibitions; preserve source evidence unchanged):\n" + self.model_dump_json(exclude={"approved"})

    def identity_text(self) -> str:
        """Shared visual contract without repeating image URLs and research evidence."""
        direction=self.direction
        if direction.startswith('Pending independent Art Director'):
            direction='Editorial hierarchy with generous whitespace and relevant source photography; choose varied compositions appropriate to each slide.'
        grammar = '; '.join(self.visual_grammar[:8])
        anti = '; '.join(self.anti_dna[:8])
        locked = '; '.join(self.deck_contract.locked[:8])
        semantic = self.semantic_graph.structure
        if self.semantic_graph.nodes:
            semantic += ": " + " -> ".join(self.semantic_graph.nodes[:10])
        archetypes = '; '.join(
            f"{item.name}: {item.composition}" for item in self.slide_archetypes[:10])
        return (f'Shared presentation identity: {self.name}. Subject: {self.subject}. '
            f'background: {self.palette.canvas}; ink: {self.palette.ink}; accent: {self.palette.accent}; muted: {self.palette.muted}. '
            f'Font: {self.font_family}. Safe margin: {self.safe_margin}px. '
            f'Use the supplied verified logo assets when enabled: {self.logo_enabled}. '
            f'Direction: {direction}\nSemantic graph: {semantic}. Approved archetypes: {archetypes}. '
            f'Visual grammar: {grammar}. Anti-DNA: {anti}. Locked deck contract: {locked}. '
            'Preserve original chart images and exact source values; rebuild tables as editable grids. '
            'Keep images relevant to the current slide and choose diagonal, brush or torn photo compositions when appropriate.')


def enrich_presentation_dna(dna: PresentationDNA, storyboard: Any | None = None) -> PresentationDNA:
    """Compile a reviewable deck-wide contract without another provider call.

    The Art Director still chooses each slide composition. This function turns
    those approved choices into a persistent contract that the UI, renderer and
    critic can share. Existing user-edited fields are preserved.
    """
    dna = dna.model_copy(deep=True)
    dna.version = "2.0"
    slides = []
    if storyboard is not None:
        raw = storyboard.model_dump(mode="json") if hasattr(storyboard, "model_dump") else storyboard
        if isinstance(raw, dict):
            slides = list(raw.get("slides") or [])
            narrative = str(raw.get("narrative_arc") or "")
            audience = str(raw.get("audience_and_goal") or "")
        else:
            narrative = audience = ""
    else:
        narrative = audience = ""

    confirmed = list(dna.evidence_tiers.confirmed)
    for item in dna.evidence:
        label = f"{item.kind}: {item.value}"
        if label not in confirmed:
            confirmed.append(label)
    dna.evidence_tiers.confirmed = confirmed[:24]
    if not dna.evidence_tiers.inferred:
        dna.evidence_tiers.inferred = [
            f"Visual direction inferred from the approved content: {dna.direction[:360]}",
            "Layout density and composition are inferred from each slide's semantic job.",
        ]
    if not dna.evidence_tiers.defaults:
        dna.evidence_tiers.defaults = [
            f"Safe margin {dna.safe_margin}px when no verified guideline overrides it.",
            "Use readable contrast and restrained decoration when brand evidence is incomplete.",
        ]

    if not dna.brand_personality.keywords:
        source = f"{dna.name} {dna.subject} {dna.direction}".casefold()
        candidates = []
        for needle, label in (("premium", "Premium"), ("fintech", "Fintech"),
                              ("technology", "Technology-led"), ("editorial", "Editorial"),
                              ("sustainable", "Sustainable"), ("green", "Sustainable"),
                              ("formal", "Formal"), ("modern", "Modern")):
            if needle in source and label not in candidates:
                candidates.append(label)
        dna.brand_personality.keywords = (candidates or ["Clear", "Credible", "Contemporary"])[:8]
        dna.brand_personality.explanation = (
            "Derived from the approved subject, content and observed brand evidence; it is not an official brand claim."
        )

    dna.typography.heading = dna.font_family
    dna.typography.body = dna.font_family
    if not dna.typography.rules:
        dna.typography.rules = [
            "Use a decisive takeaway headline rather than a generic topic label.",
            "Keep body copy readable; split dense material into another slide instead of shrinking type.",
            "Use one consistent numeric hierarchy for KPI and table values.",
        ]
    if not dna.layout_language.preferred_patterns:
        dna.layout_language.preferred_patterns = list(dict.fromkeys(dna.layouts))
    if not dna.iconography.rules:
        dna.iconography.rules = ["Use one icon family and consistent stroke weight.", "Icons support meaning; they do not replace evidence."]
    if not dna.photography.prefer:
        dna.photography.prefer = ["Slide-specific subject imagery", "Authentic product or environment photography", "Large purposeful crops"]
    if not dna.photography.avoid:
        dna.photography.avoid = ["Repeated image across slides", "Generic unrelated stock photo", "Tiny decorative thumbnails"]
    if not dna.diagram_language.rules:
        dna.diagram_language.rules = ["Preserve direction and relationship meaning.", "Limit node text and keep a visible reading order."]
    if not dna.data_visualization.rules:
        dna.data_visualization.rules = ["Preserve source values and units exactly.", "Use direct labels and emphasize the comparison that supports the takeaway."]
    if not dna.visual_grammar:
        dna.visual_grammar = [
            "One dominant visual idea per slide.",
            "Use the accent color for hierarchy and meaning, not as indiscriminate decoration.",
            "Maintain the approved palette, type family and safe margin across the deck.",
            "Vary composition by semantic job while keeping recurring navigation and footer behavior.",
            "Rebuild tables as editable grids; keep source charts as original evidence.",
        ]
    if not dna.anti_dna:
        dna.anti_dna = [
            "Dense walls of text", "Repeated card grids on consecutive slides",
            "Unrelated or duplicated photography", "Invented data or brand claims",
            "Oversized empty canvas without a deliberate focal point",
        ]

    if slides and not dna.semantic_graph.nodes:
        nodes = []
        for slide in slides:
            label = str(slide.get("section_title") or slide.get("title") or "").strip()
            if label and label not in nodes:
                nodes.append(label)
        forms = {str(slide.get("visual_form") or "") for slide in slides}
        structure = ("Process or journey" if forms & {"process", "timeline"}
                     else "Comparison and portfolio" if "comparison" in forms
                     else "Ecosystem and relationships" if "diagram" in forms
                     else "Narrative argument")
        dna.semantic_graph = SemanticGraphDNA(
            structure=structure,
            nodes=nodes[:24],
            edges=[f"{a} -> {b}" for a, b in zip(nodes, nodes[1:])][:32],
            cross_cutting=[value for value in (audience, narrative) if value][:2],
        )
    if slides and not dna.slide_archetypes:
        forms = list(dict.fromkeys(str(slide.get("visual_form") or "text") for slide in slides))
        descriptions = {
            "title": ("Open the story", "Bold cover with one focal visual and minimal copy"),
            "photo": ("Humanize a claim or show a product", "Large subject image paired with concise evidence-led copy"),
            "comparison": ("Compare alternatives on shared criteria", "Aligned columns or a highlighted comparison table"),
            "chart": ("Explain quantitative evidence", "Chart dominates; takeaway and annotation frame the result"),
            "table": ("Preserve detailed source values", "Editable grid with highlighted row or column and readable density"),
            "diagram": ("Explain a system or relationship", "Balanced nodes, clear connectors and a visible reading path"),
            "process": ("Explain sequence or mechanism", "Numbered stages with directional flow"),
            "timeline": ("Show change over time", "Time axis with milestone hierarchy"),
            "text": ("Develop an argument", "Editorial hierarchy with a supporting icon or illustration"),
            "quote": ("Create a narrative pause", "Single statement with restrained attribution"),
            "closing": ("Land the conclusion", "One memorable synthesis and next action"),
            "toc": ("Orient the audience", "Numbered chapter map with a visual anchor"),
        }
        dna.slide_archetypes = [SlideArchetypeDNA(name=form.replace("_", " ").title(),
            when_to_use=descriptions.get(form, ("Support the slide's semantic job", "Clear editorial composition"))[0],
            composition=descriptions.get(form, ("Support the slide's semantic job", "Clear editorial composition"))[1])
            for form in forms[:16]]
    if not dna.deck_contract.locked:
        dna.deck_contract.locked = [
            f"Palette {dna.palette.model_dump_json()}", f"Typography family {dna.font_family}",
            f"Safe margin {dna.safe_margin}px", "Source facts, figures, units and qualifications",
            "No image reuse unless the user explicitly approves it",
        ]
    if not dna.deck_contract.flexible:
        dna.deck_contract.flexible = [
            "Slide composition selected by the Art Director", "Image crop and treatment",
            "Number of slides when density requires a split", "Diagram geometry within preserved relationships",
        ]
    if not dna.image_prompt:
        dna.image_prompt = (
            f"Create a presentation visual for {dna.subject or dna.name}. Follow {dna.direction}. "
            f"Palette: {dna.palette.model_dump_json()}. Photography: {dna.photography.style}. "
            "Leave intentional negative space for slide copy; do not render text, logos, charts or invented data inside the image."
        )[:2400]
    return dna


def compile_presentation_dna(title: str, identity: str) -> PresentationDNA:
    """Compile supplied identity without claiming inferred tokens are official."""
    colors = list(dict.fromkeys(re.findall(r"#[0-9a-fA-F]{6}\b", identity)))
    accent = next((c for c in colors if 40 < sum(int(c[i:i+2], 16) for i in (1,3,5)) / 3 < 215), "#126B8A")
    palette = DesignPalette(accent=accent)
    aliases = {"canvas": "canvas|background", "ink": "ink|primary text|text color",
               "accent": "accent|primary accent|main accent", "muted": "muted|secondary background"}
    for role, names in aliases.items():
        match = re.search(rf"\b(?:{names})\s*[:=]\s*(#[0-9a-fA-F]{{6}})\b", identity, re.I)
        if match:
            setattr(palette, role, match.group(1))
    font = next((f for f in ("Be Vietnam Pro", "Inter", "Arial", "Roboto", "Montserrat")
                 if re.search(rf"\b{re.escape(f)}\b", identity, re.I)), "Be Vietnam Pro")
    return enrich_presentation_dna(PresentationDNA(name=title[:180] or "Source-derived editorial", subject=title[:180],
        direction=identity[:2400], palette=palette, font_family=font))
