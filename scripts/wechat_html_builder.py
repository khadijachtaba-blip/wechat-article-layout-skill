#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import mimetypes
import re
import sys
import zipfile
from pathlib import Path
from typing import Any


FONT = (
    "-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',"
    "'Hiragino Sans GB','Microsoft YaHei',Arial,sans-serif"
)
SERIF_FONT = (
    "'Songti SC','STSong','SimSun','Noto Serif CJK SC',"
    "Georgia,serif"
)
MONO_FONT = (
    "'SFMono-Regular','SF Mono','Menlo','Consolas',"
    "'Liberation Mono',monospace"
)

PALETTES = {
    "tech": {
        "accent": "#3266F5",
        "accent2": "#31BFA6",
        "dark": "#142744",
        "pale": "#EEF5FF",
        "page_bg": "#EDF1F5",
    },
    "government": {
        "accent": "#2B5F8F",
        "accent2": "#5F87AA",
        "dark": "#173A59",
        "pale": "#EFF5F9",
        "page_bg": "#EAF0F4",
    },
    "education": {
        "accent": "#3479B8",
        "accent2": "#E6A03C",
        "dark": "#183F5D",
        "pale": "#EFF7FA",
        "page_bg": "#EAF2F3",
    },
    "party": {
        "accent": "#AA3028",
        "accent2": "#C4943E",
        "dark": "#681F1A",
        "pale": "#FCF2EA",
        "page_bg": "#F3EDE8",
    },
    "culture": {
        "accent": "#96613A",
        "accent2": "#B28A58",
        "dark": "#4E3B31",
        "pale": "#F8F2E9",
        "page_bg": "#F2EDE5",
    },
    "nature": {
        "accent": "#35745A",
        "accent2": "#C07A42",
        "dark": "#29473B",
        "pale": "#EEF5F0",
        "page_bg": "#E9F0EB",
    },
    "business": {
        "accent": "#294765",
        "accent2": "#A68143",
        "dark": "#172A3D",
        "pale": "#F0F3F5",
        "page_bg": "#E9EDF0",
    },
    "editorial": {
        "accent": "#242424",
        "accent2": "#9A5B43",
        "dark": "#171717",
        "pale": "#F5F2ED",
        "page_bg": "#ECEAE6",
    },
}

KEYWORDS = {
    "party": ["党建", "党委", "廉洁", "清风", "红色", "党史", "纪检"],
    "tech": ["AI", "人工智能", "智能体", "OPC", "科技", "数字化", "平台", "软件"],
    "government": ["政府", "关工委", "调研", "委员会", "街道", "政策", "政务"],
    "education": ["教育", "学校", "教师", "学生", "课程", "青少年", "研学"],
    "culture": ["文化", "艺术", "书画", "传承", "非遗", "节庆"],
    "nature": ["文旅", "乡村", "生态", "山水", "度假", "景区"],
    "business": ["战略合作", "签约", "融资", "商务", "产业", "企业合作"],
    "editorial": ["人物", "专访", "观点", "深度", "观察", "故事", "品牌故事"],
}

LAYOUTS = {
    "briefing",
    "tech-brand",
    "minimal-news",
    "event-story",
    "education-warm",
    "business-report",
    "editorial",
    "culture-story",
}

SCENES = {
    "general",
    "official-briefing",
    "news-release",
    "party-study",
    "product-launch",
    "event-recruitment",
    "event-recap",
    "strategic-cooperation",
    "education-research",
    "policy-explainer",
    "people-story",
    "lifestyle-event",
    "culture-journey",
}

VARIANT_OPTIONS = {
    "hero_variant": {
        "scene-default",
        "brand-gradient",
        "editorial-light",
        "calendar-blocks",
        "ui-dashboard",
        "split-gradient",
    },
    "section_variant": {
        "scene-default",
        "accent-line",
        "editorial-rule",
        "label-rule",
        "ui-index",
        "number-stack",
        "gradient-underline",
    },
    "metrics_variant": {
        "scene-default",
        "dark-feature",
        "stacked-facts",
        "light-grid",
    },
    "steps_variant": {
        "scene-default",
        "rounded-cards",
        "schedule-list",
        "ticket-list",
        "ui-rail",
    },
    "emphasis_variant": {
        "scene-default",
        "gradient-statement",
        "editorial-statement",
        "ui-notice",
    },
    "points_variant": {
        "scene-default",
        "ui-list",
        "index-grid",
        "plain-checklist",
    },
}

DENSITIES = {
    "light": {
        "paragraph_margin": 24,
        "section_margin": 46,
        "article_padding": "38px 22px 48px 22px",
    },
    "balanced": {
        "paragraph_margin": 20,
        "section_margin": 42,
        "article_padding": "34px 20px 44px 20px",
    },
    "rich": {
        "paragraph_margin": 18,
        "section_margin": 36,
        "article_padding": "30px 18px 40px 18px",
    },
}


def esc(value: Any) -> str:
    return html.escape(str(value or ""))


def choose_theme(plan: dict[str, Any]) -> str:
    requested = str(plan.get("theme", "auto")).lower()
    if requested != "auto":
        if requested not in PALETTES:
            raise ValueError(f"Unsupported theme: {requested}")
        return requested

    title = str(plan.get("title", ""))
    text = f"{title}\n{plan.get('source_text', '')}"
    scores: dict[str, int] = {}
    for theme, words in KEYWORDS.items():
        score = 0
        for word in words:
            score += text.lower().count(word.lower())
            score += title.lower().count(word.lower()) * 2
        scores[theme] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "tech"


def merge_palette(plan: dict[str, Any], theme: str) -> dict[str, str]:
    palette = dict(PALETTES[theme])
    overrides = plan.get("colors") or {}
    for key in ("accent", "accent2", "dark", "pale", "page_bg"):
        if key in overrides:
            value = str(overrides[key])
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
                raise ValueError(f"Invalid color for {key}: {value}")
            palette[key] = value.upper()
    return palette


def choose_layout(plan: dict[str, Any]) -> str:
    layout = str(plan.get("layout", "")).lower()
    if layout not in LAYOUTS:
        raise ValueError(
            "layout must be one of: " + ", ".join(sorted(LAYOUTS))
        )
    return layout


def choose_scene(plan: dict[str, Any]) -> str:
    scene = str(plan.get("scene", "general")).lower()
    if scene not in SCENES:
        raise ValueError("scene must be one of: " + ", ".join(sorted(SCENES)))
    return scene


def choose_density(plan: dict[str, Any]) -> str:
    density = str(plan.get("density", "balanced")).lower()
    if density not in DENSITIES:
        raise ValueError(
            "density must be one of: " + ", ".join(sorted(DENSITIES))
        )
    return density


def choose_variants(plan: dict[str, Any], scene: str) -> dict[str, str]:
    variants: dict[str, str] = {}
    for key, allowed in VARIANT_OPTIONS.items():
        value = str(plan.get(key, "scene-default")).lower()
        if value not in allowed:
            raise ValueError(f"{key} must be one of: " + ", ".join(sorted(allowed)))
        variants[key] = value

    scene_defaults = {
        "official-briefing": {
            "hero_variant": "editorial-light",
            "section_variant": "editorial-rule",
            "metrics_variant": "stacked-facts",
            "steps_variant": "schedule-list",
            "emphasis_variant": "ui-notice",
            "points_variant": "plain-checklist",
        },
        "news-release": {
            "hero_variant": "editorial-light",
            "section_variant": "gradient-underline",
            "metrics_variant": "stacked-facts",
            "steps_variant": "schedule-list",
            "emphasis_variant": "editorial-statement",
            "points_variant": "plain-checklist",
        },
        "party-study": {
            "hero_variant": "editorial-light",
            "section_variant": "number-stack",
            "metrics_variant": "stacked-facts",
            "steps_variant": "schedule-list",
            "emphasis_variant": "editorial-statement",
            "points_variant": "plain-checklist",
        },
        "product-launch": {
            "hero_variant": "ui-dashboard",
            "section_variant": "ui-index",
            "metrics_variant": "light-grid",
            "steps_variant": "ui-rail",
            "emphasis_variant": "gradient-statement",
            "points_variant": "ui-list",
        },
        "strategic-cooperation": {
            "hero_variant": "split-gradient",
            "section_variant": "ui-index",
            "metrics_variant": "stacked-facts",
            "steps_variant": "ui-rail",
            "emphasis_variant": "ui-notice",
            "points_variant": "index-grid",
        },
        "event-recruitment": {
            "hero_variant": "calendar-blocks",
            "section_variant": "gradient-underline",
            "metrics_variant": "light-grid",
            "steps_variant": "ticket-list",
            "emphasis_variant": "gradient-statement",
            "points_variant": "ui-list",
        },
        "event-recap": {
            "hero_variant": "editorial-light",
            "section_variant": "number-stack",
            "metrics_variant": "dark-feature",
            "steps_variant": "schedule-list",
            "emphasis_variant": "editorial-statement",
            "points_variant": "index-grid",
        },
        "education-research": {
            "hero_variant": "split-gradient",
            "section_variant": "gradient-underline",
            "metrics_variant": "light-grid",
            "steps_variant": "ui-rail",
            "emphasis_variant": "ui-notice",
            "points_variant": "ui-list",
        },
        "policy-explainer": {
            "hero_variant": "editorial-light",
            "section_variant": "ui-index",
            "metrics_variant": "stacked-facts",
            "steps_variant": "schedule-list",
            "emphasis_variant": "ui-notice",
            "points_variant": "plain-checklist",
        },
        "people-story": {
            "hero_variant": "editorial-light",
            "section_variant": "number-stack",
            "metrics_variant": "stacked-facts",
            "steps_variant": "schedule-list",
            "emphasis_variant": "editorial-statement",
            "points_variant": "plain-checklist",
        },
        "lifestyle-event": {
            "hero_variant": "brand-gradient",
            "section_variant": "gradient-underline",
            "metrics_variant": "dark-feature",
            "steps_variant": "rounded-cards",
            "emphasis_variant": "gradient-statement",
            "points_variant": "index-grid",
        },
        "culture-journey": {
            "hero_variant": "editorial-light",
            "section_variant": "editorial-rule",
            "metrics_variant": "stacked-facts",
            "steps_variant": "schedule-list",
            "emphasis_variant": "editorial-statement",
            "points_variant": "plain-checklist",
        },
    }
    defaults = scene_defaults.get(
        scene,
        {
            "hero_variant": "editorial-light",
            "section_variant": "gradient-underline",
            "metrics_variant": "light-grid",
            "steps_variant": "ui-rail",
            "emphasis_variant": "ui-notice",
            "points_variant": "ui-list",
        },
    )
    for key, value in defaults.items():
        if variants[key] == "scene-default":
            variants[key] = value
    return variants


def heading_font(layout: str) -> str:
    return SERIF_FONT if layout in {"editorial", "culture-story"} else FONT


def metadata_font(layout: str) -> str:
    return MONO_FONT if layout in {"tech-brand", "editorial"} else FONT


def panel_radius(layout: str) -> str:
    if layout in {"tech-brand", "event-story", "education-warm"}:
        return "20px"
    if layout in {"briefing", "minimal-news", "business-report"}:
        return "12px"
    if layout == "culture-story":
        return "16px"
    return "0"


def data_uri_from_bytes(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def image_payload(block: dict[str, Any]) -> tuple[str, str]:
    if block.get("data_uri"):
        uri = str(block["data_uri"])
        if not uri.startswith("data:image/"):
            raise ValueError("image data_uri must start with data:image/")
        return uri, hashlib.sha256(uri.encode("utf-8")).hexdigest()

    if block.get("path"):
        path = Path(str(block["path"])).expanduser().resolve()
        data = path.read_bytes()
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        return data_uri_from_bytes(data, mime), hashlib.sha256(data).hexdigest()

    if block.get("docx_path"):
        path = Path(str(block["docx_path"])).expanduser().resolve()
        member = str(block.get("member", "word/media/image1.jpeg"))
        with zipfile.ZipFile(path) as archive:
            data = archive.read(member)
        mime = mimetypes.guess_type(member)[0] or "image/jpeg"
        return data_uri_from_bytes(data, mime), hashlib.sha256(data).hexdigest()

    raise ValueError("image block needs path, docx_path/member, or data_uri")


def body_paragraph(text: str, density: str, layout: str) -> str:
    margin = DENSITIES[density]["paragraph_margin"]
    color = "#35312E" if layout in {"editorial", "culture-story"} else "#2F3542"
    return (
        f'<p style="margin:0 0 {margin}px 0;color:{color};font-size:16px;line-height:2;'
        f'letter-spacing:0.04em;text-align:justify;font-family:{FONT};">{esc(text)}</p>'
    )


def render_header(
    plan: dict[str, Any], p: dict[str, str], layout: str, scene: str
) -> str:
    label = esc(plan.get("label", ""))
    title = esc(plan.get("title", "")).replace("\n", "<br/>")
    subtitle = esc(plan.get("subtitle", ""))
    subtitle_html = (
        f'<p style="margin:15px 0 0 0;color:#7F8798;font-size:13px;line-height:1.9;'
        f'letter-spacing:0.06em;font-family:{FONT};">{subtitle}</p>'
        if subtitle else ""
    )
    hero_variant = choose_variants(plan, scene)["hero_variant"]

    if hero_variant == "brand-gradient":
        label_html = (
            f'<p style="display:inline-block;margin:0 0 20px 0;padding:6px 12px;'
            f'color:#FFFFFF;font-size:11px;line-height:1.4;letter-spacing:0.14em;'
            f'font-weight:700;border:1px solid rgba(255,255,255,0.45);'
            f'border-radius:18px;font-family:{metadata_font(layout)};">{label}</p>'
            if label else ""
        )
        hero_subtitle = (
            f'<p style="margin:16px 0 0 0;color:#E7EDF5;font-size:13px;line-height:1.9;'
            f'letter-spacing:0.05em;font-family:{FONT};">{subtitle}</p>'
            if subtitle else ""
        )
        return (
            f'<section style="margin:0 0 34px 0;padding:29px 24px 31px;'
            f'background-color:{p["dark"]};'
            f'background-image:linear-gradient(135deg,{p["dark"]} 0%,{p["accent"]} 66%,{p["accent2"]} 145%);'
            f'border-radius:0 0 22px 22px;text-align:left;box-sizing:border-box;">'
            f'{label_html}'
            f'<h1 style="margin:0;color:#FFFFFF;font-size:33px;line-height:1.38;'
            f'letter-spacing:0.01em;font-weight:800;font-family:{FONT};">{title}</h1>'
            f'{hero_subtitle}</section>'
        )

    if hero_variant == "ui-dashboard":
        label_html = (
            f'<p style="display:inline-block;margin:0;padding:5px 9px;color:{p["accent"]};'
            f'background:#FFFFFF;border:1px solid #DCE5EE;border-radius:7px;'
            f'font-size:10px;line-height:1.5;letter-spacing:0.13em;font-weight:800;'
            f'font-family:{metadata_font(layout)};">{label}</p>'
            if label else ""
        )
        hero_subtitle = (
            f'<p style="margin:17px 0 0;padding:14px 0 0;color:#DCE5F0;'
            f'font-size:13px;line-height:1.9;letter-spacing:0.04em;'
            f'border-top:1px solid rgba(255,255,255,0.22);font-family:{FONT};">'
            f'{subtitle}</p>'
            if subtitle else ""
        )
        return (
            f'<section style="margin:0 0 34px;padding:10px;background:{p["pale"]};'
            f'border:1px solid #DCE5EE;border-radius:20px;box-sizing:border-box;">'
            f'<section style="padding:11px 12px 10px;text-align:left;">{label_html}</section>'
            f'<section style="padding:27px 23px 29px;background-color:{p["dark"]};'
            f'background-image:linear-gradient(145deg,{p["dark"]} 0%,{p["dark"]} 58%,'
            f'{p["accent"]} 150%);border-radius:14px;text-align:left;box-sizing:border-box;">'
            f'<h1 style="margin:0;color:#FFFFFF;font-size:33px;line-height:1.38;'
            f'letter-spacing:0.01em;font-weight:800;font-family:{FONT};">{title}</h1>'
            f'{hero_subtitle}</section></section>'
        )

    if hero_variant == "split-gradient":
        label_html = (
            f'<p style="margin:0;color:#FFFFFF;font-size:10px;line-height:1.5;'
            f'letter-spacing:0.16em;font-weight:800;font-family:{metadata_font(layout)};">'
            f'{label}</p>'
            if label else ""
        )
        return (
            f'<section style="margin:0 0 34px;border:1px solid #DCE3EB;'
            f'border-radius:18px;overflow:hidden;box-sizing:border-box;">'
            f'<section style="padding:13px 20px;background-color:{p["accent"]};'
            f'background-image:linear-gradient(100deg,{p["accent"]} 0%,'
            f'{p["accent2"]} 100%);text-align:left;">{label_html}</section>'
            f'<section style="padding:25px 22px 27px;background:#FFFFFF;text-align:left;">'
            f'<h1 style="margin:0;color:{p["dark"]};font-size:33px;line-height:1.4;'
            f'letter-spacing:0.01em;font-weight:800;font-family:{heading_font(layout)};">'
            f'{title}</h1>{subtitle_html}</section></section>'
        )

    if hero_variant == "editorial-light":
        label_html = (
            f'<p style="margin:0 0 16px;color:{p["accent"]};font-size:11px;'
            f'line-height:1.5;letter-spacing:0.18em;font-weight:700;'
            f'font-family:{metadata_font(layout)};">{label}</p>'
            if label else ""
        )
        return (
            f'<section style="margin:0 0 34px;padding:25px 2px 27px;text-align:left;'
            f'border-top:1px solid {p["dark"]};border-bottom:1px solid #D9DEE6;">'
            f'{label_html}<h1 style="margin:0;color:{p["dark"]};font-size:35px;'
            f'line-height:1.36;letter-spacing:0.01em;font-weight:800;'
            f'font-family:{heading_font(layout)};">{title}</h1>{subtitle_html}</section>'
        )

    if hero_variant == "calendar-blocks":
        meta_items = [
            f'<span style="display:inline-block;margin:5px 7px 0 0;padding:8px 11px;'
            f'color:{p["dark"]};background:#FFFFFF;border-top:2px solid {p["accent2"]};'
            f'font-size:12px;line-height:1.6;font-family:{FONT};">{part}</span>'
            for part in subtitle.split("｜") if part.strip()
        ]
        label_html = (
            f'<p style="display:inline-block;margin:0 0 17px;padding:6px 10px;'
            f'color:#FFFFFF;background:{p["accent"]};font-size:11px;line-height:1.4;'
            f'letter-spacing:0.12em;font-weight:700;font-family:{FONT};">{label}</p>'
            if label else ""
        )
        return (
            f'<section style="margin:0 0 34px;padding:25px 22px 27px;background:{p["pale"]};'
            f'border-radius:20px;border-top:3px solid {p["accent"]};text-align:left;'
            f'box-sizing:border-box;">{label_html}'
            f'<h1 style="margin:0;color:{p["dark"]};font-size:33px;line-height:1.4;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">{title}</h1>'
            f'<section style="margin:17px 0 0;text-align:left;">{"".join(meta_items)}</section>'
            f'</section>'
        )

    if scene == "news-release":
        label_html = (
            f'<p style="margin:0 0 14px 0;color:{p["accent"]};font-size:11px;'
            f'line-height:1.5;letter-spacing:0.16em;font-weight:700;'
            f'font-family:{FONT};">{label}</p>'
            if label else ""
        )
        return (
            f'<section style="margin:0 0 32px 0;padding:4px 0 22px;text-align:left;'
            f'border-top:1px solid #202634;border-bottom:1px solid #D9DEE6;">'
            f'{label_html}<h1 style="margin:0;color:#172033;font-size:34px;line-height:1.38;'
            f'letter-spacing:0.01em;font-weight:800;font-family:{FONT};">{title}</h1>'
            f'{subtitle_html}</section>'
        )

    if scene == "party-study":
        label_html = (
            f'<p style="margin:0 0 15px 0;color:{p["accent2"]};font-size:11px;'
            f'line-height:1.5;letter-spacing:0.18em;font-weight:700;'
            f'font-family:{FONT};">{label}</p>'
            if label else ""
        )
        return (
            f'<section style="margin:0 0 32px 0;padding:23px 0 24px;text-align:left;'
            f'border-top:4px solid {p["accent"]};border-bottom:1px solid {p["accent2"]};">'
            f'{label_html}<h1 style="margin:0;color:{p["dark"]};font-size:33px;line-height:1.42;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">{title}</h1>'
            f'{subtitle_html}</section>'
        )

    if scene == "education-research":
        label_html = (
            f'<p style="margin:0 0 13px 0;color:{p["accent"]};font-size:11px;'
            f'line-height:1.5;letter-spacing:0.16em;font-weight:700;'
            f'font-family:{FONT};">{label}</p>'
            if label else ""
        )
        return (
            f'<section style="margin:0 0 32px 0;padding:24px 0 23px;'
            f'border-top:1px solid {p["accent"]};border-bottom:4px solid {p["pale"]};'
            f'box-sizing:border-box;text-align:left;">{label_html}'
            f'<h1 style="margin:0;color:{p["dark"]};font-size:32px;line-height:1.42;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">{title}</h1>'
            f'{subtitle_html}</section>'
        )

    if scene == "product-launch":
        label_html = (
            f'<p style="display:inline-block;margin:0 0 18px 0;padding:5px 9px;'
            f'color:{p["dark"]};background:#FFFFFF;font-size:10px;line-height:1.4;'
            f'letter-spacing:0.16em;font-weight:800;font-family:{MONO_FONT};">{label}</p>'
            if label else ""
        )
        hero_subtitle = (
            f'<p style="margin:19px 0 0;padding:14px 0 0;color:#E7EDF5;font-size:13px;'
            f'line-height:1.9;letter-spacing:0.05em;border-top:1px solid rgba(255,255,255,0.25);'
            f'font-family:{FONT};">{subtitle}</p>'
            if subtitle else ""
        )
        return (
            f'<section style="margin:0 0 34px 0;padding:0;background:{p["pale"]};'
            f'border-radius:20px;overflow:hidden;box-sizing:border-box;">'
            f'<section style="padding:27px 23px 29px;background:{p["dark"]};text-align:left;">'
            f'{label_html}<h1 style="margin:0;color:#FFFFFF;font-size:33px;line-height:1.38;'
            f'letter-spacing:0.01em;font-weight:800;font-family:{FONT};">{title}</h1>'
            f'{hero_subtitle}</section>'
            f'<section style="height:10px;background:{p["accent"]};font-size:0;line-height:0;">&nbsp;</section>'
            f'</section>'
        )

    if scene == "event-recap":
        label_html = (
            f'<p style="margin:0 0 14px 0;color:{p["accent"]};font-size:11px;'
            f'line-height:1.5;letter-spacing:0.2em;font-weight:700;'
            f'font-family:{metadata_font(layout)};">{label}</p>'
            if label else ""
        )
        return (
            f'<section style="margin:0 0 30px 0;padding:4px 0 24px;text-align:left;'
            f'border-bottom:1px solid #E1E7EE;">{label_html}'
            f'<h1 style="margin:0;color:{p["dark"]};font-size:34px;line-height:1.4;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">{title}</h1>'
            f'{subtitle_html}</section>'
        )

    if scene == "lifestyle-event":
        label_html = (
            f'<p style="display:inline-block;margin:0 0 17px 0;padding:6px 10px;'
            f'color:#FFFFFF;background:{p["accent"]};font-size:11px;line-height:1.4;'
            f'letter-spacing:0.12em;font-weight:700;font-family:{FONT};">{label}</p>'
            if label else ""
        )
        return (
            f'<section style="margin:0 0 34px 0;padding:24px 21px 26px;'
            f'background:{p["pale"]};border-top:8px solid {p["accent2"]};'
            f'border-bottom:1px dashed {p["accent"]};text-align:left;box-sizing:border-box;">'
            f'{label_html}<h1 style="margin:0;color:{p["dark"]};font-size:33px;line-height:1.4;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">{title}</h1>'
            f'{subtitle_html}</section>'
        )

    if layout == "editorial":
        label_html = (
            f'<p style="margin:0 0 20px 0;color:{p["accent2"]};font-size:11px;'
            f'line-height:1.6;letter-spacing:0.2em;font-weight:700;'
            f'font-family:{MONO_FONT};">{label}</p>'
            if label else ""
        )
        return (
            f'<section style="margin:0 0 36px 0;padding:0 0 28px 0;text-align:left;'
            f'border-bottom:1px solid #D7D2CA;">{label_html}'
            f'<h1 style="margin:0;color:{p["dark"]};font-size:35px;line-height:1.34;'
            f'letter-spacing:0.01em;font-weight:800;font-family:{SERIF_FONT};">{title}</h1>'
            f'{subtitle_html}</section>'
        )

    if layout == "culture-story":
        label_html = (
            f'<p style="margin:0 0 18px 0;color:{p["accent"]};font-size:12px;'
            f'line-height:1.6;letter-spacing:0.18em;font-weight:700;'
            f'font-family:{FONT};">{label}</p>'
            if label else ""
        )
        return (
            f'<section style="margin:0 0 36px 0;padding:25px 6px;text-align:center;'
            f'border-top:1px solid {p["accent2"]};border-bottom:1px solid {p["accent2"]};">'
            f'{label_html}<h1 style="margin:0;color:{p["dark"]};font-size:33px;'
            f'line-height:1.42;letter-spacing:0.04em;font-weight:700;'
            f'font-family:{SERIF_FONT};">{title}</h1>{subtitle_html}</section>'
        )

    if layout in {"briefing", "minimal-news", "business-report"}:
        label_html = (
            f'<p style="margin:0 0 16px 0;color:{p["accent"]};font-size:11px;'
            f'line-height:1.5;letter-spacing:0.18em;font-weight:700;'
            f'font-family:{metadata_font(layout)};">{label}</p>'
            if label else ""
        )
        rule = (
            f'<p style="margin:18px 0 0 0;width:58px;height:3px;background:{p["accent"]};'
            f'font-size:0;line-height:0;">&nbsp;</p>'
        )
        return (
            f'<section style="margin:0 0 30px 0;padding:0 0 22px 0;text-align:left;'
            f'border-bottom:1px solid #E6E9EF;">'
            f'{label_html}'
            f'<h1 style="margin:0;color:#172033;font-size:32px;line-height:1.4;'
            f'letter-spacing:0.01em;font-weight:800;font-family:{FONT};">{title}</h1>'
            f'{subtitle_html}{rule}</section>'
        )

    label_html = (
        f'<p style="display:inline-block;margin:0 0 20px 0;padding:6px 12px;'
        f'color:#FFFFFF;font-size:11px;line-height:1.4;letter-spacing:0.14em;'
        f'font-weight:700;border:1px solid rgba(255,255,255,0.45);'
        f'border-radius:18px;font-family:{metadata_font(layout)};">{label}</p>'
        if label else ""
    )
    hero_subtitle = (
        f'<p style="margin:16px 0 0 0;color:#E7EDF5;font-size:13px;line-height:1.9;'
        f'letter-spacing:0.05em;font-family:{FONT};">{subtitle}</p>'
        if subtitle else ""
    )
    return (
        f'<section style="margin:0 0 34px 0;padding:29px 24px 31px;'
        f'background-color:{p["dark"]};'
        f'background-image:linear-gradient(135deg,{p["dark"]} 0%,{p["accent"]} 66%,{p["accent2"]} 145%);'
        f'border-radius:0 0 22px 22px;text-align:left;box-sizing:border-box;">'
        f'{label_html}'
        f'<h1 style="margin:0;color:#FFFFFF;font-size:33px;line-height:1.38;'
        f'letter-spacing:0.01em;font-weight:800;font-family:{FONT};">{title}</h1>'
        f'{hero_subtitle}</section>'
    )


def render_lead(items: list[str], p: dict[str, str], layout: str, scene: str) -> str:
    if not items:
        return ""
    content = "".join(
        f'<p style="margin:{"0" if i == len(items)-1 else "0 0 14px 0"};'
        f'color:#343B4F;font-size:16px;line-height:2;letter-spacing:0.04em;'
        f'text-align:justify;font-family:{FONT};">{esc(item)}</p>'
        for i, item in enumerate(items)
    )
    if scene == "news-release":
        return (
            f'<section style="margin:0 0 32px 0;padding:18px 0;'
            f'border-top:1px solid #D9DEE6;border-bottom:1px solid #D9DEE6;'
            f'box-sizing:border-box;">{content}</section>'
        )
    if scene == "official-briefing":
        return (
            f'<section style="margin:0 0 30px 0;padding:19px 0;'
            f'border-top:2px solid {p["accent"]};border-bottom:1px solid #DDE3EA;'
            f'box-sizing:border-box;">{content}</section>'
        )
    if scene == "lifestyle-event":
        return (
            f'<section style="margin:0 0 28px 0;padding:22px 21px;background:{p["pale"]};'
            f'border-top:3px solid {p["accent"]};border-right:1px solid #E1E7EE;'
            f'border-bottom:1px solid #E1E7EE;border-radius:20px;box-sizing:border-box;">'
            f'{content}</section>'
        )
    if layout == "editorial":
        return (
            f'<section style="margin:0 0 34px 0;padding:0 0 0 22px;'
            f'border-left:3px solid {p["accent2"]};box-sizing:border-box;">'
            f'{content.replace("color:#343B4F", "color:#4A423D")}</section>'
        )
    if layout == "culture-story":
        return (
            f'<section style="margin:0 0 34px 0;padding:24px 22px;'
            f'background:{p["pale"]};border-top:1px solid {p["accent2"]};'
            f'border-bottom:1px solid {p["accent2"]};box-sizing:border-box;">'
            f'{content.replace("color:#343B4F", "color:#51453D").replace(FONT, SERIF_FONT)}</section>'
        )
    if layout == "minimal-news":
        return (
            f'<section style="margin:0 0 30px 0;padding:0 0 0 17px;'
            f'border-left:3px solid {p["accent"]};box-sizing:border-box;">'
            f"{content}</section>"
        )
    if layout == "business-report":
        return (
            f'<section style="margin:0 0 28px 0;padding:21px;background:{p["dark"]};'
            f'border-radius:{panel_radius(layout)};box-sizing:border-box;">'
            f'{content.replace("color:#343B4F", "color:#F5F7FB")}</section>'
        )
    border_side = "border-left" if layout in {"briefing", "education-warm"} else "border-top"
    return (
        f'<section style="margin:0 0 26px 0;padding:22px 21px;background:{p["pale"]};'
        f'{border_side}:3px solid {p["accent"]};border-radius:{panel_radius(layout)};'
        f'border-right:1px solid #E1E7EE;border-bottom:1px solid #E1E7EE;'
        f'box-sizing:border-box;">'
        f"{content}</section>"
    )


def render_section(
    block: dict[str, Any],
    p: dict[str, str],
    layout: str,
    density: str,
    scene: str,
    section_variant: str,
) -> str:
    number = esc(block.get("number", ""))
    title = esc(block.get("title", ""))
    label = esc(block.get("label") or (f"SECTION {number}" if number else "SECTION"))
    margin = DENSITIES[density]["section_margin"]

    if section_variant == "ui-index":
        index_text = number or (label if label and not label.startswith("SECTION") else "•")
        meta_html = (
            f'<p style="margin:0 0 6px;color:{p["accent"]};font-size:10px;line-height:1.5;'
            f'letter-spacing:0.15em;font-weight:800;font-family:{metadata_font(layout)};">'
            f'{label}</p>'
            if label and not label.startswith("SECTION") and label != index_text else ""
        )
        return (
            f'<section style="margin:{margin}px 0 23px;padding:0 0 13px;'
            f'border-bottom:1px solid #DCE3EA;text-align:left;box-sizing:border-box;">'
            f'<span style="display:inline-block;vertical-align:top;min-width:34px;margin:1px 12px 0 0;'
            f'padding:7px 8px;color:#FFFFFF;background:{p["dark"]};border-radius:7px;'
            f'font-size:11px;line-height:1.35;text-align:center;font-weight:800;'
            f'font-family:{MONO_FONT};box-sizing:border-box;">{index_text}</span>'
            f'<section style="display:inline-block;vertical-align:top;width:82%;'
            f'box-sizing:border-box;">{meta_html}'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:23px;line-height:1.48;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{heading_font(layout)};">'
            f'{title}</h2></section></section>'
        )

    if section_variant == "number-stack":
        index_html = (
            f'<p style="margin:0 0 7px;color:{p["accent2"]};font-size:34px;line-height:1;'
            f'letter-spacing:-0.04em;font-weight:800;font-family:{MONO_FONT};">{number}</p>'
            if number else ""
        )
        label_html = (
            f'<p style="margin:0 0 7px;color:{p["accent"]};font-size:10px;line-height:1.5;'
            f'letter-spacing:0.16em;font-weight:800;font-family:{metadata_font(layout)};">'
            f'{label}</p>'
            if label and not label.startswith("SECTION") else ""
        )
        return (
            f'<section style="margin:{margin}px 0 24px;padding:18px 0 0;'
            f'border-top:1px solid {p["dark"]};text-align:left;">{index_html}{label_html}'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:24px;line-height:1.46;'
            f'letter-spacing:0.01em;font-weight:800;font-family:{heading_font(layout)};">'
            f'{title}</h2></section>'
        )

    if section_variant == "gradient-underline":
        label_html = (
            f'<p style="margin:0 0 7px;color:{p["accent"]};font-size:10px;line-height:1.5;'
            f'letter-spacing:0.16em;font-weight:800;font-family:{metadata_font(layout)};">'
            f'{label}</p>'
            if label and not label.startswith("SECTION") else ""
        )
        number_html = (
            f'<span style="margin:0 10px 0 0;color:{p["accent"]};font-size:13px;'
            f'font-weight:800;font-family:{MONO_FONT};">{number}</span>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 23px;text-align:left;">{label_html}'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:23px;line-height:1.5;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{heading_font(layout)};">'
            f'{number_html}{title}</h2>'
            f'<p style="margin:13px 0 0;width:88px;height:3px;background-color:{p["accent"]};'
            f'background-image:linear-gradient(90deg,{p["accent"]} 0%,'
            f'{p["accent2"]} 100%);font-size:0;line-height:0;">&nbsp;</p></section>'
        )

    if section_variant == "accent-line":
        label_html = (
            f'<p style="margin:0 0 7px;color:{p["accent"]};font-size:11px;line-height:1.5;'
            f'letter-spacing:0.16em;font-weight:700;font-family:{metadata_font(layout)};">'
            f'{label}</p>'
            if label and not label.startswith("SECTION") else ""
        )
        return (
            f'<section style="margin:{margin}px 0 22px;padding-left:14px;'
            f'border-left:4px solid {p["accent2"]};text-align:left;">{label_html}'
            f'<h2 style="margin:0;color:#1F2633;font-size:23px;line-height:1.5;'
            f'letter-spacing:0.03em;font-weight:700;font-family:{heading_font(layout)};">'
            f'{title}</h2></section>'
        )

    if section_variant == "editorial-rule":
        label_html = (
            f'<p style="margin:0 0 8px;color:{p["accent"]};font-size:11px;line-height:1.5;'
            f'letter-spacing:0.16em;font-weight:700;font-family:{metadata_font(layout)};">'
            f'{label}</p>'
            if label and not label.startswith("SECTION") else ""
        )
        return (
            f'<section style="margin:{margin}px 0 23px;padding:17px 0 13px;'
            f'border-top:1px solid {p["dark"]};border-bottom:1px solid #DDE3EA;'
            f'text-align:left;">{label_html}'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:23px;line-height:1.5;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{heading_font(layout)};">'
            f'{title}</h2></section>'
        )

    if section_variant == "label-rule":
        number_html = (
            f'<span style="display:inline-block;margin:0 8px 0 0;color:#FFFFFF;'
            f'font-size:11px;line-height:1.5;font-weight:800;font-family:{MONO_FONT};">'
            f'{number}</span>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 22px;padding:0 0 12px;text-align:left;'
            f'border-bottom:1px solid {p["accent2"]};">'
            f'<p style="display:inline-block;margin:0 0 9px;padding:4px 8px;color:#FFFFFF;'
            f'background:{p["accent"]};font-size:10px;line-height:1.5;letter-spacing:0.1em;'
            f'font-weight:700;font-family:{FONT};">{number_html}{label}</p>'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:23px;line-height:1.5;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{heading_font(layout)};">'
            f'{title}</h2></section>'
        )

    if scene == "party-study":
        number_html = (
            f'<span style="display:inline-block;margin:0 10px 0 0;padding:4px 7px;'
            f'color:#FFFFFF;background:{p["accent"]};font-size:12px;line-height:1.4;'
            f'font-weight:800;font-family:{MONO_FONT};">{number}</span>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 23px 0;padding:0 0 12px;'
            f'border-bottom:1px solid {p["accent2"]};text-align:left;">'
            f'<p style="margin:0 0 9px;color:{p["accent2"]};font-size:11px;line-height:1.5;'
            f'letter-spacing:0.16em;font-weight:700;font-family:{FONT};">{label}</p>'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:23px;line-height:1.5;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">'
            f'{number_html}{title}</h2></section>'
        )

    if scene == "product-launch":
        number_html = (
            f'<span style="display:inline-block;vertical-align:middle;margin:0 13px 0 0;'
            f'color:{p["accent"]};font-size:28px;line-height:1;font-weight:800;'
            f'letter-spacing:-0.04em;font-family:{MONO_FONT};">{number}</span>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 23px;padding:18px 0 0;'
            f'border-top:1px solid #CDD6E0;text-align:left;">'
            f'<p style="margin:0 0 8px;color:{p["accent2"]};font-size:10px;line-height:1.5;'
            f'letter-spacing:0.2em;font-weight:700;font-family:{MONO_FONT};">{label}</p>'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:24px;line-height:1.45;'
            f'letter-spacing:0.01em;font-weight:800;font-family:{FONT};">'
            f'{number_html}{title}</h2></section>'
        )

    if scene == "news-release":
        return (
            f'<section style="margin:{margin}px 0 22px;padding:0 0 11px;text-align:left;'
            f'border-bottom:1px solid #202634;">'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:22px;line-height:1.5;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">{title}</h2>'
            f'<p style="margin:8px 0 0;width:42px;height:2px;background:{p["accent"]};'
            f'font-size:0;line-height:0;">&nbsp;</p></section>'
        )

    if scene == "event-recruitment":
        label_html = (
            f'<p style="margin:0 0 10px;color:{p["accent"]};font-size:10px;line-height:1.5;'
            f'letter-spacing:0.2em;font-weight:700;font-family:{MONO_FONT};">'
            f'<span style="display:inline-block;width:18px;height:1px;vertical-align:middle;'
            f'margin:0 8px 0 0;background:{p["accent2"]};font-size:0;line-height:0;">&nbsp;</span>'
            f'{label}'
            f'<span style="display:inline-block;width:18px;height:1px;vertical-align:middle;'
            f'margin:0 0 0 8px;background:{p["accent2"]};font-size:0;line-height:0;">&nbsp;</span>'
            f'</p>'
        )
        number_html = (
            f'<span style="display:block;margin:0 0 6px;color:{p["accent2"]};font-size:12px;'
            f'line-height:1.2;letter-spacing:0.18em;font-weight:800;font-family:{MONO_FONT};">{number}</span>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 24px;padding:0 0 16px;text-align:center;'
            f'border-bottom:1px solid #D8E1E3;">{number_html}{label_html}'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:24px;line-height:1.48;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">{title}</h2></section>'
        )

    if scene == "event-recap":
        number_html = (
            f'<span style="display:inline-block;vertical-align:top;margin:-2px 12px 0 0;'
            f'color:{p["pale"]};font-size:42px;line-height:0.9;font-weight:800;'
            f'font-family:{MONO_FONT};">{number}</span>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 24px;padding:0 0 13px;text-align:left;'
            f'border-bottom:2px solid {p["accent"]};">'
            f'<p style="margin:0 0 7px;color:{p["accent"]};font-size:11px;line-height:1.5;'
            f'letter-spacing:0.16em;font-weight:700;font-family:{FONT};">{label}</p>'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:24px;line-height:1.45;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">'
            f'{number_html}{title}</h2></section>'
        )

    if scene == "official-briefing":
        number_html = (
            f'<span style="margin-right:10px;color:{p["accent"]};font-size:13px;'
            f'font-family:{MONO_FONT};font-weight:800;">{number} /</span>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 22px;padding:16px 0 0;text-align:left;'
            f'border-top:2px solid {p["accent"]};">'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:23px;line-height:1.5;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">'
            f'{number_html}{title}</h2></section>'
        )

    if scene == "policy-explainer":
        topic = label if label and not label.startswith("SECTION") else "政策要点"
        number_html = (
            f'<span style="color:{p["accent"]};font-family:{MONO_FONT};font-weight:800;">{number}</span>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 22px;padding:15px 0 12px;text-align:left;'
            f'border-top:1px solid {p["dark"]};border-bottom:1px solid #DDE3EA;">'
            f'<p style="margin:0 0 7px;color:{p["accent"]};font-size:11px;line-height:1.5;'
            f'letter-spacing:0.12em;font-weight:700;font-family:{FONT};">{topic} {number_html}</p>'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:23px;line-height:1.5;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">{title}</h2></section>'
        )

    if scene == "strategic-cooperation":
        number_html = (
            f'<span style="display:inline-block;vertical-align:middle;margin:0 10px 0 0;'
            f'width:28px;height:28px;color:#FFFFFF;background:{p["dark"]};font-size:12px;'
            f'line-height:28px;text-align:center;font-weight:800;font-family:{MONO_FONT};">{number}</span>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 22px;padding:0 0 13px;text-align:left;'
            f'border-bottom:1px solid #DDE3EA;">'
            f'<p style="margin:0 0 8px;color:{p["accent2"]};font-size:11px;line-height:1.5;'
            f'letter-spacing:0.16em;font-weight:700;font-family:{FONT};">{label}</p>'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:23px;line-height:1.5;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">'
            f'{number_html}{title}</h2></section>'
        )

    if scene == "education-research":
        number_html = (
            f'<span style="display:inline-block;vertical-align:middle;margin:0 9px 0 0;'
            f'padding:3px 7px;color:#FFFFFF;background:{p["accent2"]};'
            f'font-size:11px;line-height:1.5;text-align:center;font-weight:800;font-family:{MONO_FONT};">{number}</span>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 22px;padding:0 0 12px;text-align:left;'
            f'border-bottom:4px solid {p["pale"]};">'
            f'<p style="margin:0 0 7px;color:{p["accent"]};font-size:11px;line-height:1.5;'
            f'letter-spacing:0.14em;font-weight:700;font-family:{FONT};">{label}</p>'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:23px;line-height:1.5;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">'
            f'{number_html}{title}</h2></section>'
        )

    if scene == "lifestyle-event":
        number_html = (
            f'<span style="display:inline-block;margin:0 8px 0 0;color:#FFFFFF;opacity:0.85;'
            f'font-size:11px;line-height:1.5;font-weight:800;font-family:{MONO_FONT};">{number}</span>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 22px;padding:0 0 12px;text-align:left;'
            f'border-bottom:1px dashed {p["accent2"]};">'
            f'<p style="display:inline-block;margin:0 0 8px;padding:4px 8px;color:#FFFFFF;'
            f'background:{p["accent"]};font-size:10px;line-height:1.5;letter-spacing:0.1em;'
            f'font-weight:700;font-family:{FONT};">{number_html}{label}</p>'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:23px;line-height:1.5;'
            f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">{title}</h2></section>'
        )

    if layout == "editorial":
        number_html = (
            f'<p style="margin:0 0 10px 0;color:{p["accent2"]};font-size:48px;'
            f'line-height:0.95;letter-spacing:-0.04em;font-weight:800;'
            f'font-family:{MONO_FONT};">{number}</p>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 24px 0;padding:25px 0 0 0;'
            f'border-top:1px solid #D7D2CA;text-align:left;">{number_html}'
            f'<p style="margin:0 0 7px 0;color:{p["accent2"]};font-size:11px;'
            f'line-height:1.5;letter-spacing:0.18em;font-weight:700;'
            f'font-family:{MONO_FONT};">{label}</p>'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:24px;line-height:1.45;'
            f'letter-spacing:0.01em;font-weight:700;font-family:{SERIF_FONT};">'
            f'{title}</h2></section>'
        )

    if layout == "culture-story":
        return (
            f'<section style="margin:{margin}px 0 24px 0;text-align:center;">'
            f'<p style="margin:0 0 9px 0;color:{p["accent2"]};font-size:12px;'
            f'line-height:1.5;letter-spacing:0.16em;font-weight:700;'
            f'font-family:{FONT};">{label}</p>'
            f'<h2 style="margin:0;color:{p["dark"]};font-size:23px;line-height:1.5;'
            f'letter-spacing:0.06em;font-weight:700;font-family:{SERIF_FONT};">{title}</h2>'
            f'<p style="margin:14px auto 0 auto;width:72px;height:1px;'
            f'background:{p["accent2"]};font-size:0;line-height:0;">&nbsp;</p></section>'
        )

    if layout in {"briefing", "business-report"}:
        number_html = (
            f'<span style="display:inline-block;margin-right:11px;color:{p["accent"]};'
            f'font-size:15px;line-height:1.5;font-weight:800;'
            f'font-family:{MONO_FONT};">{number}</span>'
            if number else ""
        )
        return (
            f'<section style="margin:{margin}px 0 22px 0;padding:0 0 11px 14px;'
            f'border-left:4px solid {p["accent"]};border-bottom:1px solid #DDE3EA;'
            f'text-align:left;">'
            f'<h2 style="margin:0;color:#1F2633;font-size:23px;line-height:1.5;'
            f'letter-spacing:0.02em;font-weight:700;font-family:{FONT};">'
            f'{number_html}{title}</h2></section>'
        )

    if layout == "minimal-news":
        return (
            f'<section style="margin:{margin}px 0 21px 0;text-align:left;">'
            f'<p style="margin:0 0 7px 0;color:{p["accent"]};font-size:12px;'
            f'line-height:1.5;letter-spacing:0.12em;font-weight:700;'
            f'font-family:{FONT};">{label}</p>'
            f'<h2 style="margin:0;padding-left:13px;border-left:4px solid {p["accent"]};'
            f'color:#1F2633;font-size:21px;line-height:1.55;letter-spacing:0.02em;'
            f'font-weight:700;font-family:{FONT};">{title}</h2></section>'
        )

    if layout == "event-story":
        return (
            f'<section style="margin:{margin}px 0 22px 0;padding-left:14px;'
            f'border-left:4px solid {p["accent2"]};text-align:left;">'
            f'<p style="margin:0 0 7px 0;color:{p["accent"]};font-size:11px;line-height:1.5;'
            f'letter-spacing:0.18em;font-weight:700;'
            f'font-family:{FONT};">{label}</p>'
            f'<h2 style="margin:0;color:#1F2633;font-size:23px;line-height:1.5;'
            f'letter-spacing:0.03em;font-weight:700;font-family:{FONT};">{title}</h2>'
            f'</section>'
        )

    if layout == "education-warm":
        return (
            f'<section style="margin:{margin}px 0 22px 0;padding:0 0 12px 14px;'
            f'border-left:4px solid {p["accent2"]};border-bottom:1px solid #DDE6EA;'
            f'text-align:left;">'
            f'<p style="margin:0 0 6px 0;color:{p["accent"]};font-size:11px;'
            f'line-height:1.5;letter-spacing:0.16em;font-weight:700;'
            f'font-family:{FONT};">{label}</p>'
            f'<h2 style="margin:0;color:#1F2633;font-size:23px;line-height:1.5;'
            f'letter-spacing:0.02em;font-weight:700;font-family:{FONT};">{title}</h2>'
            f'</section>'
        )

    return (
        f'<section style="margin:{margin}px 0 22px 0;padding-left:14px;'
        f'border-left:4px solid {p["accent2"]};text-align:left;">'
        f'<p style="margin:0 0 9px 0;color:{p["accent"]};font-size:12px;line-height:1.4;'
        f'letter-spacing:0.18em;font-weight:700;font-family:{FONT};">{label}</p>'
        f'<h2 style="margin:0;color:#1F2633;font-size:23px;line-height:1.5;'
        f'letter-spacing:0.03em;font-weight:700;font-family:{FONT};">{title}</h2>'
        f'</section>'
    )


def render_block(
    block: dict[str, Any],
    p: dict[str, str],
    layout: str,
    density: str,
    scene: str,
    variants: dict[str, str],
) -> tuple[str, dict[str, str] | None]:
    kind = str(block.get("type", "")).lower()

    if kind == "paragraph":
        return body_paragraph(str(block.get("text", "")), density, layout), None

    if kind == "image":
        uri, digest = image_payload(block)
        alt = esc(block.get("alt", "文章图片"))
        radius = (
            "0"
            if layout == "editorial"
            else "8px"
            if layout in {"briefing", "minimal-news", "business-report"}
            else panel_radius(layout)
        )
        return (
            f'<section style="margin:26px 0 30px 0;padding:0;">'
            f'<img src="{uri}" alt="{alt}" style="display:block;width:100%;height:auto;'
            f'margin:0;border-radius:{radius};box-sizing:border-box;" /></section>',
            {"sha256": digest, "alt": str(block.get("alt", ""))},
        )

    if kind == "section":
        return (
            render_section(
                block,
                p,
                layout,
                density,
                scene,
                variants["section_variant"],
            ),
            None,
        )

    if kind == "subheading":
        title = esc(block.get("title", ""))
        label = esc(block.get("label", ""))
        label_html = (
            f'<span style="display:inline-block;margin:0 8px 0 0;color:{p["accent"]};'
            f'font-size:10px;line-height:1.5;letter-spacing:0.12em;font-weight:800;'
            f'font-family:{metadata_font(layout)};">{label}</span>'
            if label else ""
        )
        if layout in {"editorial", "culture-story"}:
            return (
                f'<section style="margin:30px 0 16px;padding:0 0 8px;'
                f'border-bottom:1px solid #E2DDD6;text-align:left;">'
                f'<h3 style="margin:0;color:{p["dark"]};font-size:18px;line-height:1.65;'
                f'letter-spacing:0.03em;font-weight:700;font-family:{SERIF_FONT};">'
                f'{label_html}{title}</h3></section>',
                None,
            )
        return (
            f'<section style="margin:28px 0 15px;padding:0;text-align:left;">'
            f'<h3 style="margin:0;color:{p["dark"]};font-size:18px;line-height:1.65;'
            f'letter-spacing:0.03em;font-weight:800;font-family:{FONT};">'
            f'{label_html}{title}</h3>'
            f'<p style="margin:8px 0 0;width:32px;height:2px;background:{p["accent2"]};'
            f'font-size:0;line-height:0;">&nbsp;</p></section>',
            None,
        )

    if kind == "keyline":
        label = esc(block.get("label", ""))
        text = esc(block.get("text", ""))
        emphasis_variant = variants["emphasis_variant"]
        label_on_dark = (
            f'<p style="margin:0 0 12px;color:#FFFFFF;opacity:0.8;font-size:10px;'
            f'line-height:1.5;letter-spacing:0.16em;font-weight:800;'
            f'font-family:{metadata_font(layout)};">{label}</p>'
            if label else ""
        )
        if emphasis_variant == "gradient-statement":
            return (
                f'<section style="margin:30px 0;padding:25px 22px;'
                f'background-color:{p["dark"]};'
                f'background-image:linear-gradient(135deg,{p["dark"]} 0%,'
                f'{p["accent"]} 78%,{p["accent2"]} 145%);'
                f'border-radius:{panel_radius(layout)};box-sizing:border-box;">'
                f'{label_on_dark}<p style="margin:0;color:#FFFFFF;font-size:20px;'
                f'line-height:1.72;letter-spacing:0.03em;font-weight:700;'
                f'font-family:{heading_font(layout)};">{text}</p></section>',
                None,
            )
        if emphasis_variant == "editorial-statement":
            label_html = (
                f'<p style="margin:0 0 10px;color:{p["accent"]};font-size:10px;'
                f'line-height:1.5;letter-spacing:0.17em;font-weight:800;'
                f'font-family:{metadata_font(layout)};">{label}</p>'
                if label else ""
            )
            return (
                f'<section style="margin:32px 0;padding:25px 0;'
                f'border-top:1px solid {p["dark"]};border-bottom:1px solid #D8DEE6;">'
                f'{label_html}<p style="margin:0;color:{p["dark"]};font-size:21px;'
                f'line-height:1.72;letter-spacing:0.025em;font-weight:700;'
                f'font-family:{heading_font(layout)};">{text}</p></section>',
                None,
            )
        label_html = (
            f'<p style="margin:0 0 8px;color:{p["accent"]};font-size:10px;line-height:1.5;'
            f'letter-spacing:0.15em;font-weight:800;font-family:{metadata_font(layout)};">'
            f'{label}</p>'
            if label else ""
        )
        return (
            f'<section style="margin:28px 0;padding:19px 20px;background:{p["pale"]};'
            f'border:1px solid #DCE4EB;border-top:4px solid {p["accent"]};'
            f'border-radius:{panel_radius(layout)};box-sizing:border-box;">'
            f'{label_html}<p style="margin:0;color:{p["dark"]};font-size:18px;'
            f'line-height:1.8;letter-spacing:0.03em;font-weight:700;'
            f'font-family:{heading_font(layout)};">{text}</p></section>',
            None,
        )

    if kind == "keypoints":
        raw_items = list(block.get("items", []))
        items: list[dict[str, str]] = []
        for item in raw_items:
            if isinstance(item, dict):
                items.append(
                    {
                        "title": esc(item.get("title", "")),
                        "text": esc(item.get("text", "")),
                    }
                )
            else:
                items.append({"title": esc(item), "text": ""})
        label = esc(block.get("label", ""))
        points_variant = variants["points_variant"]
        label_html = (
            f'<p style="margin:0 0 14px;color:{p["accent"]};font-size:10px;line-height:1.5;'
            f'letter-spacing:0.16em;font-weight:800;font-family:{metadata_font(layout)};">'
            f'{label}</p>'
            if label else ""
        )
        rendered_items: list[str] = []
        if points_variant == "index-grid":
            width = "47%" if len(items) > 1 else "100%"
            for index, item in enumerate(items, start=1):
                text_html = (
                    f'<p style="margin:6px 0 0;color:#697184;font-size:13px;line-height:1.8;'
                    f'font-family:{FONT};">{item["text"]}</p>'
                    if item["text"] else ""
                )
                rendered_items.append(
                    f'<section style="display:inline-block;width:{width};vertical-align:top;'
                    f'margin:5px 1%;padding:15px 14px;background:#FFFFFF;'
                    f'border:1px solid #DCE4EB;border-radius:{panel_radius(layout)};'
                    f'box-sizing:border-box;text-align:left;">'
                    f'<p style="margin:0 0 9px;color:{p["accent"]};font-size:11px;'
                    f'line-height:1.4;font-weight:800;font-family:{MONO_FONT};">{index:02d}</p>'
                    f'<p style="margin:0;color:{p["dark"]};font-size:15px;line-height:1.65;'
                    f'font-weight:800;font-family:{FONT};">{item["title"]}</p>'
                    f'{text_html}</section>'
                )
            return (
                f'<section style="margin:24px 0 28px;padding:17px 12px;'
                f'background:{p["pale"]};border-radius:{panel_radius(layout)};'
                f'box-sizing:border-box;text-align:center;">{label_html}'
                f'{"".join(rendered_items)}</section>',
                None,
            )
        if points_variant == "plain-checklist":
            for index, item in enumerate(items, start=1):
                text_html = (
                    f'<p style="margin:4px 0 0;color:#697184;font-size:13px;line-height:1.85;'
                    f'font-family:{FONT};">{item["text"]}</p>'
                    if item["text"] else ""
                )
                rendered_items.append(
                    f'<section style="margin:0;padding:14px 0;border-bottom:1px solid #E0E5EB;'
                    f'box-sizing:border-box;text-align:left;">'
                    f'<span style="display:inline-block;vertical-align:top;width:31px;'
                    f'color:{p["accent"]};font-size:11px;line-height:1.7;font-weight:800;'
                    f'font-family:{MONO_FONT};">{index:02d}</span>'
                    f'<section style="display:inline-block;vertical-align:top;width:89%;">'
                    f'<p style="margin:0;color:{p["dark"]};font-size:15px;line-height:1.7;'
                    f'font-weight:800;font-family:{FONT};">{item["title"]}</p>'
                    f'{text_html}</section></section>'
                )
            return (
                f'<section style="margin:24px 0 28px;border-top:2px solid {p["dark"]};">'
                f'{label_html}{"".join(rendered_items)}</section>',
                None,
            )
        for index, item in enumerate(items, start=1):
            text_html = (
                f'<p style="margin:4px 0 0;color:#697184;font-size:13px;line-height:1.85;'
                f'font-family:{FONT};">{item["text"]}</p>'
                if item["text"] else ""
            )
            rendered_items.append(
                f'<section style="margin:0 0 10px;padding:14px 15px;background:#FFFFFF;'
                f'border:1px solid #DCE4EB;border-radius:10px;box-sizing:border-box;'
                f'text-align:left;">'
                f'<span style="display:inline-block;vertical-align:top;margin:1px 11px 0 0;'
                f'padding:4px 6px;color:#FFFFFF;background:{p["accent"]};border-radius:5px;'
                f'font-size:10px;line-height:1.4;font-weight:800;font-family:{MONO_FONT};">'
                f'{index:02d}</span>'
                f'<section style="display:inline-block;vertical-align:top;width:82%;">'
                f'<p style="margin:0;color:{p["dark"]};font-size:15px;line-height:1.7;'
                f'font-weight:800;font-family:{FONT};">{item["title"]}</p>'
                f'{text_html}</section></section>'
            )
        return (
            f'<section style="margin:24px 0 28px;padding:18px 16px 9px;'
            f'background:{p["pale"]};border:1px solid #DCE4EB;'
            f'border-radius:{panel_radius(layout)};box-sizing:border-box;">'
            f'{label_html}{"".join(rendered_items)}</section>',
            None,
        )

    if kind == "callout":
        label = esc(block.get("label", "重点内容"))
        text = esc(block.get("text", ""))
        if scene == "party-study":
            return (
                f'<section style="margin:0 0 28px 0;padding:21px 20px;background:{p["pale"]};'
                f'border-top:1px solid {p["accent2"]};border-bottom:1px solid {p["accent2"]};'
                f'border-left:4px solid {p["accent"]};box-sizing:border-box;">'
                f'<p style="margin:0 0 9px 0;color:{p["accent"]};font-size:13px;line-height:1.6;'
                f'letter-spacing:0.12em;font-weight:700;font-family:{FONT};">{label}</p>'
                f'<p style="margin:0;color:#3B302D;font-size:16px;line-height:2;letter-spacing:0.04em;'
                f'text-align:justify;font-family:{FONT};">{text}</p></section>',
                None,
            )
        if scene in {"official-briefing", "policy-explainer"}:
            return (
                f'<section style="margin:0 0 28px 0;padding:5px 0 5px 18px;'
                f'border-left:4px solid {p["accent"]};box-sizing:border-box;">'
                f'<p style="margin:0 0 8px 0;color:{p["accent"]};font-size:12px;line-height:1.6;'
                f'letter-spacing:0.12em;font-weight:700;font-family:{FONT};">{label}</p>'
                f'<p style="margin:0;color:#2F3542;font-size:16px;line-height:2;letter-spacing:0.04em;'
                f'text-align:justify;font-family:{FONT};">{text}</p></section>',
                None,
            )
        if layout == "editorial":
            return (
                f'<section style="margin:0 0 30px 0;padding:26px 24px;'
                f'border:1px solid #D7D2CA;border-left:4px solid {p["accent2"]};'
                f'box-sizing:border-box;">'
                f'<p style="margin:0 0 10px 0;color:{p["accent2"]};font-size:11px;'
                f'line-height:1.6;letter-spacing:0.18em;font-weight:700;'
                f'font-family:{MONO_FONT};">{label}</p>'
                f'<p style="margin:0;color:#35312E;font-size:17px;line-height:1.95;'
                f'letter-spacing:0.03em;text-align:justify;font-family:{SERIF_FONT};">'
                f'{text}</p></section>',
                None,
            )
        if layout == "culture-story":
            return (
                f'<section style="margin:0 0 30px 0;padding:25px 22px;'
                f'background:{p["pale"]};border-top:1px solid {p["accent2"]};'
                f'border-bottom:1px solid {p["accent2"]};box-sizing:border-box;text-align:center;">'
                f'<p style="margin:0 0 10px 0;color:{p["accent"]};font-size:12px;'
                f'line-height:1.6;letter-spacing:0.16em;font-weight:700;'
                f'font-family:{FONT};">{label}</p>'
                f'<p style="margin:0;color:#51453D;font-size:16px;line-height:2;'
                f'letter-spacing:0.04em;font-family:{SERIF_FONT};">{text}</p></section>',
                None,
            )
        if layout == "minimal-news":
            return (
                f'<section style="margin:0 0 28px 0;padding:18px 0;'
                f'border-top:1px solid {p["accent"]};border-bottom:1px solid {p["accent"]};">'
                f'<p style="margin:0 0 8px 0;color:{p["accent"]};font-size:13px;'
                f'line-height:1.6;letter-spacing:0.1em;font-weight:700;'
                f'font-family:{FONT};">{label}</p>'
                f'<p style="margin:0;color:#2F3542;font-size:16px;line-height:2;'
                f'letter-spacing:0.04em;text-align:justify;font-family:{FONT};">'
                f'{text}</p></section>',
                None,
            )
        if layout in {"tech-brand", "business-report"}:
            return (
                f'<section style="margin:0 0 28px 0;padding:22px;background:{p["dark"]};'
                f'border-radius:{panel_radius(layout)};box-sizing:border-box;">'
                f'<p style="margin:0 0 9px 0;color:{p["accent2"]};font-size:13px;'
                f'line-height:1.6;letter-spacing:0.12em;font-weight:700;'
                f'font-family:{FONT};">{label}</p>'
                f'<p style="margin:0;color:#FFFFFF;font-size:16px;line-height:2;'
                f'letter-spacing:0.04em;text-align:justify;font-family:{FONT};">'
                f'{text}</p></section>',
                None,
            )
        return (
            f'<section style="margin:0 0 28px 0;padding:22px;background:{p["pale"]};'
            f'border:1px solid #E1E7EE;border-radius:{panel_radius(layout)};'
            f'box-sizing:border-box;">'
            f'<p style="margin:0 0 10px 0;color:{p["accent"]};font-size:13px;line-height:1.6;'
            f'letter-spacing:0.12em;font-weight:700;font-family:{FONT};">{label}</p>'
            f'<p style="margin:0;color:#2F3542;font-size:16px;line-height:2;'
            f'letter-spacing:0.04em;text-align:justify;font-family:{FONT};">{text}</p></section>',
            None,
        )

    if kind == "tags":
        items = [str(x) for x in block.get("items", [])]
        pieces: list[str] = []
        tag_radius = "0" if layout == "editorial" else "16px"
        for i, item in enumerate(items):
            if i:
                pieces.append(f'<span style="color:#A1A6B3;font-size:13px;">＋</span>')
            pieces.append(
                f'<span style="display:inline-block;margin:4px;padding:5px 10px;'
                f'color:{p["accent"]};font-size:13px;line-height:1.5;background:{p["pale"]};'
                f'border:1px solid #E1E7EE;border-radius:{tag_radius};'
                f'font-family:{metadata_font(layout)};">{esc(item)}</span>'
            )
        return f'<section style="margin:22px 0 28px 0;text-align:center;line-height:2.5;">{"".join(pieces)}</section>', None

    if kind == "metrics":
        items = list(block.get("items", []))
        columns = []
        width = "47%" if len(items) <= 2 else "31%"
        metric_radius = panel_radius(layout)
        metrics_variant = variants["metrics_variant"]
        if metrics_variant == "dark-feature":
            for item in items:
                columns.append(
                    f'<section style="display:inline-block;width:{width};vertical-align:top;'
                    f'box-sizing:border-box;margin:5px 0;">'
                    f'<p style="margin:0;color:#FFFFFF;font-size:28px;line-height:1.35;'
                    f'font-weight:800;font-family:{metadata_font(layout)};">'
                    f'{esc(item.get("value", ""))}</p>'
                    f'<p style="margin:4px 0 0;color:#E1E4EA;font-size:13px;line-height:1.7;'
                    f'font-family:{FONT};">{esc(item.get("label", ""))}</p></section>'
                )
            return (
                f'<section style="margin:22px 0 20px;padding:20px 14px;'
                f'background:{p["dark"]};border-radius:{metric_radius};'
                f'box-sizing:border-box;text-align:center;">{"".join(columns)}</section>',
                None,
            )
        if metrics_variant == "stacked-facts":
            for item in items:
                columns.append(
                    f'<section style="display:block;margin:0;padding:11px 0;'
                    f'border-bottom:1px solid #DDE3EA;box-sizing:border-box;text-align:left;">'
                    f'<p style="display:inline-block;width:36%;margin:0;color:{p["accent"]};'
                    f'font-size:22px;line-height:1.45;font-weight:800;vertical-align:middle;'
                    f'font-family:{metadata_font(layout)};">{esc(item.get("value", ""))}</p>'
                    f'<p style="display:inline-block;width:60%;margin:0;color:#60697A;'
                    f'font-size:13px;line-height:1.7;vertical-align:middle;'
                    f'font-family:{FONT};">{esc(item.get("label", ""))}</p></section>'
                )
            return (
                f'<section style="margin:22px 0 20px;padding:6px 0;'
                f'border-top:2px solid {p["accent"]};">{"".join(columns)}</section>',
                None,
            )
        if metrics_variant == "light-grid":
            for item in items:
                columns.append(
                    f'<section style="display:inline-block;width:{width};vertical-align:top;'
                    f'margin:5px 1%;padding:16px 12px;background:{p["pale"]};'
                    f'border-top:3px solid {p["accent"]};border-radius:{metric_radius};'
                    f'box-sizing:border-box;text-align:left;">'
                    f'<p style="margin:0;color:{p["dark"]};font-size:25px;line-height:1.35;'
                    f'font-weight:800;font-family:{metadata_font(layout)};">'
                    f'{esc(item.get("value", ""))}</p>'
                    f'<p style="margin:5px 0 0;color:#60697A;font-size:13px;line-height:1.7;'
                    f'font-family:{FONT};">{esc(item.get("label", ""))}</p></section>'
                )
            return (
                f'<section style="margin:22px 0 20px;text-align:center;">'
                f'{"".join(columns)}</section>',
                None,
            )
        if scene == "official-briefing":
            for item in items:
                columns.append(
                    f'<section style="display:block;margin:0;padding:10px 0;'
                    f'border-bottom:1px solid #DDE3EA;box-sizing:border-box;text-align:left;">'
                    f'<p style="display:inline-block;width:34%;margin:0;color:{p["accent"]};'
                    f'font-size:24px;line-height:1.4;font-weight:800;vertical-align:middle;'
                    f'font-family:{metadata_font(layout)};">{esc(item.get("value", ""))}</p>'
                    f'<p style="display:inline-block;width:62%;margin:0;color:#60697A;'
                    f'font-size:13px;line-height:1.7;vertical-align:middle;'
                    f'font-family:{FONT};">{esc(item.get("label", ""))}</p></section>'
                )
            return (
                f'<section style="margin:22px 0 20px 0;padding:5px 0;text-align:left;'
                f'border-top:2px solid {p["accent"]};">'
                f'{"".join(columns)}</section>',
                None,
            )
        if scene in {"news-release", "strategic-cooperation", "lifestyle-event"}:
            for item in items:
                columns.append(
                    f'<section style="display:block;margin:0;padding:10px 0;'
                    f'border-bottom:1px solid #DDE3EA;box-sizing:border-box;text-align:left;">'
                    f'<p style="display:inline-block;width:36%;margin:0;color:{p["accent"]};'
                    f'font-size:22px;line-height:1.45;font-weight:800;vertical-align:middle;'
                    f'font-family:{metadata_font(layout)};">{esc(item.get("value", ""))}</p>'
                    f'<p style="display:inline-block;width:60%;margin:0;color:#60697A;'
                    f'font-size:13px;line-height:1.7;vertical-align:middle;'
                    f'font-family:{FONT};">{esc(item.get("label", ""))}</p></section>'
                )
            border_style = "dashed" if scene == "lifestyle-event" else "solid"
            return (
                f'<section style="margin:22px 0 20px;padding:6px 0;'
                f'border-top:1px {border_style} {p["accent"]};">'
                f'{"".join(columns)}</section>',
                None,
            )
        for item in items:
            columns.append(
                f'<section style="display:inline-block;width:{width};vertical-align:top;'
                f'box-sizing:border-box;margin:5px 0;">'
                f'<p style="margin:0;color:#FFFFFF;font-size:28px;line-height:1.35;'
                f'font-weight:800;font-family:{metadata_font(layout)};">{esc(item.get("value", ""))}</p>'
                f'<p style="margin:4px 0 0 0;color:#E1E4EA;font-size:13px;line-height:1.7;'
                f'font-family:{FONT};">{esc(item.get("label", ""))}</p></section>'
            )
        return (
            f'<section style="margin:22px 0 20px 0;padding:20px 14px;background:{p["dark"]};'
            f'border-radius:{metric_radius};box-sizing:border-box;text-align:center;">{"".join(columns)}</section>',
            None,
        )

    if kind == "features":
        items = [esc(x) for x in block.get("items", [])]
        lines = []
        feature_radius = panel_radius(layout)
        if scene == "strategic-cooperation":
            for item in items:
                lines.append(
                    f'<span style="display:inline-block;width:47%;vertical-align:top;margin:5px 1%;'
                    f'padding:12px 10px;color:{p["dark"]};font-size:14px;line-height:1.7;'
                    f'border-top:2px solid {p["accent2"]};background:#FFFFFF;box-sizing:border-box;'
                    f'font-family:{FONT};">{item}</span>'
                )
            return (
                f'<section style="margin:0 0 26px 0;padding:12px 8px;background:{p["pale"]};'
                f'border-radius:{feature_radius};box-sizing:border-box;text-align:center;">'
                f'{"".join(lines)}</section>',
                None,
            )
        for index in range(0, len(items), 3):
            lines.append(" · ".join(items[index:index + 3]))
        return (
            f'<section style="margin:0 0 26px 0;padding:16px 18px;background:{p["pale"]};'
            f'border-radius:{feature_radius};text-align:center;box-sizing:border-box;">'
            f'<p style="margin:0;color:{p["accent"]};font-size:13px;line-height:2;'
            f'letter-spacing:0.04em;font-family:{FONT};">{"<br/>".join(lines)}</p></section>',
            None,
        )

    if kind == "timeline":
        items = list(block.get("items", []))
        rendered_items = []
        timeline_radius = panel_radius(layout)
        for index, item in enumerate(items):
            bottom = "0" if index == len(items) - 1 else "18px"
            text = esc(item.get("text", ""))
            text_html = (
                f'<p style="margin:5px 0 0 0;color:#60697A;font-size:14px;line-height:1.9;'
                f'letter-spacing:0.03em;font-family:{FONT};">{text}</p>'
                if text else ""
            )
            rendered_items.append(
                f'<section style="margin:0 0 {bottom} 0;padding:0 0 0 18px;'
                f'border-left:2px solid {p["accent"]};box-sizing:border-box;">'
                f'<p style="margin:0 0 4px 0;color:{p["accent"]};font-size:13px;'
                f'line-height:1.5;font-weight:700;letter-spacing:0.06em;'
                f'font-family:{FONT};">{esc(item.get("time", ""))}</p>'
                f'<p style="margin:0;color:#242B3A;font-size:16px;line-height:1.7;'
                f'font-weight:700;font-family:{FONT};">{esc(item.get("title", ""))}</p>'
                f'{text_html}</section>'
            )
        if scene == "event-recap":
            return (
                f'<section style="margin:24px 0 30px 0;padding:0 0 0 4px;box-sizing:border-box;">'
                f'{"".join(rendered_items)}</section>',
                None,
            )
        return (
            f'<section style="margin:24px 0 30px 0;padding:22px 20px;'
            f'background:{p["pale"]};border-radius:{timeline_radius};box-sizing:border-box;">'
            f'{"".join(rendered_items)}</section>',
            None,
        )

    if kind == "steps":
        items = list(block.get("items", []))
        rendered_items = []
        step_radius = panel_radius(layout)
        steps_variant = variants["steps_variant"]
        if steps_variant == "rounded-cards":
            for index, item in enumerate(items, start=1):
                text = esc(item.get("text", ""))
                text_html = (
                    f'<p style="margin:5px 0 0;color:#60697A;font-size:14px;line-height:1.9;'
                    f'letter-spacing:0.03em;font-family:{FONT};">{text}</p>'
                    if text else ""
                )
                rendered_items.append(
                    f'<section style="margin:0 0 14px;padding:15px 16px;background:#FFFFFF;'
                    f'border:1px solid #E1E7EE;border-radius:{step_radius};box-sizing:border-box;">'
                    f'<span style="display:inline-block;vertical-align:top;width:28px;height:28px;'
                    f'color:#FFFFFF;background:{p["accent"]};border-radius:50%;font-size:13px;'
                    f'line-height:28px;text-align:center;font-weight:700;font-family:{FONT};">'
                    f'{index:02d}</span>'
                    f'<section style="display:inline-block;vertical-align:top;width:84%;'
                    f'margin-left:10px;"><p style="margin:1px 0 0;color:#242B3A;'
                    f'font-size:16px;line-height:1.7;font-weight:700;font-family:{FONT};">'
                    f'{esc(item.get("title", ""))}</p>{text_html}</section></section>'
                )
            return (
                f'<section style="margin:22px 0 28px;">{"".join(rendered_items)}</section>',
                None,
            )
        if steps_variant == "schedule-list":
            for index, item in enumerate(items, start=1):
                text = esc(item.get("text", ""))
                text_html = (
                    f'<p style="margin:5px 0 0;color:#60697A;font-size:14px;line-height:1.9;'
                    f'letter-spacing:0.03em;font-family:{FONT};">{text}</p>'
                    if text else ""
                )
                rendered_items.append(
                    f'<section style="margin:0;padding:15px 0;border-bottom:1px solid #DDE3EA;'
                    f'box-sizing:border-box;"><span style="display:inline-block;vertical-align:top;'
                    f'margin:1px 12px 0 0;padding:4px 7px;color:#FFFFFF;'
                    f'background:{p["accent"]};font-size:11px;line-height:1.5;'
                    f'text-align:center;font-weight:800;font-family:{MONO_FONT};">'
                    f'{index:02d}</span><section style="display:inline-block;vertical-align:top;'
                    f'width:80%;"><p style="margin:0;color:#242B3A;font-size:16px;line-height:1.7;'
                    f'font-weight:700;font-family:{FONT};">{esc(item.get("title", ""))}</p>'
                    f'{text_html}</section></section>'
                )
            return (
                f'<section style="margin:22px 0 28px;border-top:2px solid {p["accent"]};">'
                f'{"".join(rendered_items)}</section>',
                None,
            )
        if steps_variant == "ticket-list":
            for index, item in enumerate(items, start=1):
                text = esc(item.get("text", ""))
                text_html = (
                    f'<p style="margin:5px 0 0;color:#60697A;font-size:14px;line-height:1.9;'
                    f'letter-spacing:0.03em;font-family:{FONT};">{text}</p>'
                    if text else ""
                )
                rendered_items.append(
                    f'<section style="margin:0 0 12px;padding:15px 16px;background:{p["pale"]};'
                    f'border-left:4px solid {p["accent2"]};border-radius:0 {step_radius} '
                    f'{step_radius} 0;box-sizing:border-box;">'
                    f'<p style="margin:0 0 5px;color:{p["accent"]};font-size:11px;line-height:1.5;'
                    f'font-weight:800;letter-spacing:0.12em;font-family:{MONO_FONT};">'
                    f'{index:02d}</p><p style="margin:0;color:#242B3A;font-size:16px;line-height:1.7;'
                    f'font-weight:700;font-family:{FONT};">{esc(item.get("title", ""))}</p>'
                    f'{text_html}</section>'
                )
            return (
                f'<section style="margin:22px 0 28px;">{"".join(rendered_items)}</section>',
                None,
            )
        if steps_variant == "ui-rail":
            for index, item in enumerate(items, start=1):
                text = esc(item.get("text", ""))
                text_html = (
                    f'<p style="margin:5px 0 0;color:#697184;font-size:13px;line-height:1.85;'
                    f'letter-spacing:0.02em;font-family:{FONT};">{text}</p>'
                    if text else ""
                )
                rendered_items.append(
                    f'<section style="margin:0 0 10px;padding:14px 15px;background:#FFFFFF;'
                    f'border:1px solid #DCE4EB;border-radius:10px;box-sizing:border-box;">'
                    f'<span style="display:inline-block;vertical-align:top;margin:1px 12px 0 0;'
                    f'padding:5px 7px;color:#FFFFFF;background:{p["dark"]};border-radius:5px;'
                    f'font-size:10px;line-height:1.4;font-weight:800;font-family:{MONO_FONT};">'
                    f'{index:02d}</span>'
                    f'<section style="display:inline-block;vertical-align:top;width:82%;">'
                    f'<p style="margin:0;color:{p["dark"]};font-size:15px;line-height:1.7;'
                    f'font-weight:800;font-family:{FONT};">'
                    f'{esc(item.get("title", ""))}</p>{text_html}</section></section>'
                )
            return (
                f'<section style="margin:22px 0 28px;padding:18px 16px 8px;'
                f'background:{p["pale"]};border-top:4px solid {p["accent"]};'
                f'border-radius:{step_radius};box-sizing:border-box;">'
                f'{"".join(rendered_items)}</section>',
                None,
            )
        if scene in {"education-research", "lifestyle-event", "policy-explainer"}:
            for index, item in enumerate(items, start=1):
                text = esc(item.get("text", ""))
                text_html = (
                    f'<p style="margin:5px 0 0;color:#60697A;font-size:14px;line-height:1.9;'
                    f'letter-spacing:0.03em;font-family:{FONT};">{text}</p>'
                    if text else ""
                )
                border_style = "dashed" if scene == "lifestyle-event" else "solid"
                rendered_items.append(
                    f'<section style="margin:0;padding:15px 0;'
                    f'border-bottom:1px {border_style} #DDE3EA;box-sizing:border-box;">'
                    f'<span style="display:inline-block;vertical-align:top;margin:1px 12px 0 0;'
                    f'padding:4px 7px;color:#FFFFFF;background:{p["accent"]};'
                    f'font-size:11px;line-height:1.5;text-align:center;font-weight:800;'
                    f'font-family:{MONO_FONT};">{index:02d}</span>'
                    f'<section style="display:inline-block;vertical-align:top;width:80%;">'
                    f'<p style="margin:0;color:#242B3A;font-size:16px;line-height:1.7;'
                    f'font-weight:700;font-family:{FONT};">{esc(item.get("title", ""))}</p>'
                    f'{text_html}</section></section>'
                )
            top_border = (
                f'border-top:4px solid {p["pale"]};'
                if scene == "education-research"
                else f'border-top:1px {border_style} {p["accent"]};'
            )
            return (
                f'<section style="margin:22px 0 28px;padding:0;{top_border}">'
                f'{"".join(rendered_items)}</section>',
                None,
            )
        number_radius = (
            "0"
            if layout == "editorial"
            or scene in {"product-launch", "event-recruitment", "strategic-cooperation"}
            else "50%"
        )
        for index, item in enumerate(items, start=1):
            text = esc(item.get("text", ""))
            text_html = (
                f'<p style="margin:5px 0 0 0;color:#60697A;font-size:14px;line-height:1.9;'
                f'letter-spacing:0.03em;font-family:{FONT};">{text}</p>'
                if text else ""
            )
            rendered_items.append(
                f'<section style="margin:0 0 14px 0;padding:15px 16px;'
                f'background:#FFFFFF;border:1px solid #E1E7EE;'
                f'border-radius:{step_radius};box-sizing:border-box;">'
                f'<span style="display:inline-block;vertical-align:top;width:28px;height:28px;'
                f'color:#FFFFFF;background:{p["accent"]};border-radius:{number_radius};font-size:13px;'
                f'line-height:28px;text-align:center;font-weight:700;'
                f'font-family:{FONT};">{index:02d}</span>'
                f'<section style="display:inline-block;vertical-align:top;width:84%;'
                f'margin-left:10px;">'
                f'<p style="margin:1px 0 0 0;color:#242B3A;font-size:16px;line-height:1.7;'
                f'font-weight:700;font-family:{FONT};">{esc(item.get("title", ""))}</p>'
                f'{text_html}</section></section>'
            )
        return f'<section style="margin:22px 0 28px 0;">{"".join(rendered_items)}</section>', None

    if kind == "caption":
        return (
            f'<p style="margin:-20px 0 28px 0;color:#8A91A3;font-size:12px;line-height:1.8;'
            f'letter-spacing:0.03em;text-align:center;font-family:{FONT};">'
            f'{esc(block.get("text", ""))}</p>',
            None,
        )

    if kind == "quote":
        label = esc(block.get("label", ""))
        text = esc(block.get("text", ""))
        attribution = esc(block.get("attribution", ""))
        if layout == "editorial":
            attribution_html = (
                f'<p style="margin:16px 0 0 0;color:{p["accent2"]};font-size:12px;'
                f'line-height:1.8;text-align:right;font-family:{MONO_FONT};">— {attribution}</p>'
                if attribution else ""
            )
            label_html = (
                f'<p style="margin:0 0 11px 0;color:{p["accent2"]};font-size:11px;'
                f'line-height:1.6;letter-spacing:0.18em;font-weight:700;'
                f'font-family:{MONO_FONT};">{label}</p>'
                if label else ""
            )
            return (
                f'<section style="margin:34px 0;padding:30px 0;border-top:1px solid #D7D2CA;'
                f'border-bottom:1px solid #D7D2CA;box-sizing:border-box;">{label_html}'
                f'<p style="margin:0;color:{p["dark"]};font-size:22px;line-height:1.65;'
                f'letter-spacing:0.02em;font-weight:600;font-family:{SERIF_FONT};">{text}</p>'
                f'{attribution_html}</section>',
                None,
            )
        if layout == "culture-story":
            attribution_html = (
                f'<p style="margin:14px 0 0 0;color:{p["accent"]};font-size:13px;'
                f'line-height:1.8;text-align:right;font-family:{FONT};">— {attribution}</p>'
                if attribution else ""
            )
            return (
                f'<section style="margin:32px 0;padding:27px 22px;background:{p["pale"]};'
                f'border-left:2px solid {p["accent2"]};box-sizing:border-box;">'
                f'<p style="margin:0;color:#51453D;font-size:18px;line-height:1.9;'
                f'letter-spacing:0.04em;font-family:{SERIF_FONT};">{text}</p>'
                f'{attribution_html}</section>',
                None,
            )
        label_html = (
            f'<p style="margin:0 0 9px 0;color:{p["accent"]};font-size:13px;line-height:1.6;'
            f'letter-spacing:0.1em;font-weight:700;font-family:{FONT};">{label}</p>'
            if label else ""
        )
        attribution_html = (
            f'<p style="margin:12px 0 0 0;color:{p["accent"]};font-size:14px;line-height:1.8;'
            f'font-weight:600;text-align:right;font-family:{FONT};">— {attribution}</p>'
            if attribution else ""
        )
        return (
            f'<section style="margin:25px 0;padding:22px;background:{p["pale"]};'
            f'border-left:4px solid {p["accent"]};'
            f'border-radius:0 {panel_radius(layout)} {panel_radius(layout)} 0;'
            f'box-sizing:border-box;">{label_html}'
            f'<p style="margin:0;color:#30364A;font-size:16px;line-height:2;'
            f'letter-spacing:0.04em;text-align:justify;font-family:{FONT};">{text}</p>'
            f'{attribution_html}</section>',
            None,
        )

    if kind == "closing":
        closing_subtitle = esc(block.get("subtitle", ""))
        closing_subtitle_html = (
            f'<p style="margin:0;color:#746B65;font-size:14px;line-height:1.9;'
            f'letter-spacing:0.04em;font-family:{FONT};">{closing_subtitle}</p>'
            if closing_subtitle else ""
        )
        if layout in {"editorial", "culture-story"}:
            alignment = "left" if layout == "editorial" else "center"
            return (
                f'<section style="margin:38px 0 0 0;padding:28px 0;'
                f'border-top:1px solid {p["accent2"]};text-align:{alignment};'
                f'box-sizing:border-box;">'
                f'<p style="margin:0 0 9px 0;color:{p["dark"]};font-size:21px;line-height:1.6;'
                f'font-weight:700;letter-spacing:0.03em;font-family:{SERIF_FONT};">'
                f'{esc(block.get("title", ""))}</p>'
                f'{closing_subtitle_html}</section>',
                None,
            )
        standard_subtitle_html = (
            f'<p style="margin:0;color:#656C7D;font-size:14px;line-height:1.9;'
            f'letter-spacing:0.05em;font-family:{FONT};">{closing_subtitle}</p>'
            if closing_subtitle else ""
        )
        return (
            f'<section style="margin:28px 0 0 0;padding:24px 18px;background:{p["pale"]};'
            f'border-radius:{panel_radius(layout)};text-align:center;box-sizing:border-box;">'
            f'<p style="margin:0 0 8px 0;color:{p["accent"]};font-size:18px;line-height:1.7;'
            f'font-weight:700;letter-spacing:0.04em;font-family:{FONT};">{esc(block.get("title", ""))}</p>'
            f'{standard_subtitle_html}</section>',
            None,
        )

    raise ValueError(f"Unsupported block type: {kind}")


def render_article(
    plan: dict[str, Any],
    palette: dict[str, str],
    layout: str,
    density: str,
    scene: str,
) -> tuple[str, list[dict[str, str]]]:
    padding = DENSITIES[density]["article_padding"]
    blocks = list(plan.get("blocks", []))
    variants = choose_variants(plan, scene)
    images: list[dict[str, str]] = []
    parts = [
        '<section id="wechat-article" style="max-width:677px;margin:0 auto;'
        f'padding:{padding};background:#FFFFFF;box-sizing:border-box;word-break:break-word;">',
    ]

    if scene == "event-recap" and blocks and str(blocks[0].get("type", "")).lower() == "image":
        rendered, image_info = render_block(
            blocks.pop(0), palette, layout, density, scene, variants
        )
        parts.append(rendered)
        if image_info:
            images.append(image_info)

    parts.extend(
        [
            render_header(plan, palette, layout, scene),
            render_lead([str(x) for x in plan.get("lead", [])], palette, layout, scene),
        ]
    )

    for block in blocks:
        rendered, image_info = render_block(
            block, palette, layout, density, scene, variants
        )
        parts.append(rendered)
        if image_info:
            images.append(image_info)
    parts.append("</section>")
    return "".join(parts), images


COPY_SCRIPT = """
<script>
(function () {
  var button = document.getElementById('copyButton');
  var article = document.getElementById('wechat-article');
  button.addEventListener('click', function () {
    var range = document.createRange();
    range.selectNode(article);
    var selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    selection.removeAllRanges();
    button.textContent = ok ? '已复制，可粘贴' : '请按 Ctrl+C 复制';
    if (!ok) { selection.addRange(range); }
    setTimeout(function () { button.textContent = '复制全部富文本'; }, 2600);
  });
}());
</script>
""".strip()


def document_shell(title: str, article: str, page_bg: str, controls: bool) -> str:
    toolbar = ""
    script = ""
    if controls:
        toolbar = (
            f'<div style="position:sticky;top:0;z-index:99;padding:12px 16px;'
            f'background:#172033;color:#FFFFFF;text-align:center;font-family:{FONT};'
            f'box-shadow:0 2px 12px rgba(18,25,50,.18);">'
            f'<span style="margin-right:12px;font-size:14px;">打开后点击右侧按钮，再粘贴到公众号编辑器</span>'
            f'<button id="copyButton" type="button" style="padding:8px 18px;color:#FFFFFF;'
            f'background:#6A5CFF;border:0;border-radius:5px;font-size:14px;font-weight:700;'
            f'cursor:pointer;">复制全部富文本</button></div>'
        )
        script = COPY_SCRIPT
    return (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\" />"
        '<meta name="viewport" content="width=device-width,initial-scale=1" />'
        f"<title>{esc(title)}</title></head>"
        f'<body style="margin:0;background:{page_bg};">{toolbar}'
        f'<main style="padding:24px 10px 48px 10px;">{article}</main>{script}</body></html>\n'
    )


def validate_plan(plan: dict[str, Any]) -> None:
    if not str(plan.get("title", "")).strip():
        raise ValueError("title is required")
    choose_layout(plan)
    scene = choose_scene(plan)
    choose_density(plan)
    choose_variants(plan, scene)
    if not isinstance(plan.get("blocks", []), list):
        raise ValueError("blocks must be a list")
    output = plan.get("output") or {}
    if not output.get("directory") or not output.get("stem"):
        raise ValueError("output.directory and output.stem are required")


def load_plan(path: str) -> dict[str, Any]:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build WeChat-compatible rich-text and clean HTML.")
    parser.add_argument("plan", help="JSON plan path, or - to read JSON from stdin")
    args = parser.parse_args()

    plan = load_plan(args.plan)
    validate_plan(plan)
    theme = choose_theme(plan)
    layout = choose_layout(plan)
    scene = choose_scene(plan)
    density = choose_density(plan)
    variants = choose_variants(plan, scene)
    palette = merge_palette(plan, theme)
    article, images = render_article(plan, palette, layout, density, scene)

    output = plan["output"]
    out_dir = Path(str(output["directory"])).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = str(output["stem"]).strip()
    rich_path = out_dir / f"{stem}_富文本版_打开后复制.html"
    clean_path = out_dir / f"{stem}_HTML纯净版.html"

    rich_path.write_text(
        document_shell(str(plan["title"]), article, palette["page_bg"], True),
        encoding="utf-8",
    )
    clean_path.write_text(
        document_shell(str(plan["title"]), article, palette["page_bg"], False),
        encoding="utf-8",
    )

    result = {
        "theme": theme,
        "layout": layout,
        "scene": scene,
        "density": density,
        "variants": variants,
        "palette": palette,
        "rich_text_html": str(rich_path),
        "clean_html": str(clean_path),
        "image_count": len(images),
        "images": images,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
