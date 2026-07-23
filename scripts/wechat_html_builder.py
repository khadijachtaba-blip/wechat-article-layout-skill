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

PALETTES = {
    "tech": {
        "accent": "#6A5CFF",
        "accent2": "#4F7CFF",
        "dark": "#20294A",
        "pale": "#F2F1FF",
        "page_bg": "#EEF1F7",
    },
    "government": {
        "accent": "#2457A6",
        "accent2": "#3A72C5",
        "dark": "#17365F",
        "pale": "#EEF5FC",
        "page_bg": "#EDF2F7",
    },
    "education": {
        "accent": "#2F6FD6",
        "accent2": "#24A19C",
        "dark": "#164A74",
        "pale": "#EFF8FA",
        "page_bg": "#EEF5F7",
    },
    "party": {
        "accent": "#B42318",
        "accent2": "#D6A13B",
        "dark": "#6D1711",
        "pale": "#FFF4EC",
        "page_bg": "#F7F1ED",
    },
    "culture": {
        "accent": "#A65E2E",
        "accent2": "#C89B5D",
        "dark": "#523D31",
        "pale": "#FBF5EC",
        "page_bg": "#F6F1EA",
    },
    "nature": {
        "accent": "#2E7D5B",
        "accent2": "#77A86A",
        "dark": "#24483A",
        "pale": "#F1F8F3",
        "page_bg": "#EDF4EF",
    },
    "business": {
        "accent": "#1E3A5F",
        "accent2": "#A6854A",
        "dark": "#16263B",
        "pale": "#F2F5F8",
        "page_bg": "#EDF1F5",
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


def body_paragraph(text: str) -> str:
    return (
        f'<p style="margin:0 0 20px 0;color:#2F3542;font-size:16px;line-height:2;'
        f'letter-spacing:0.04em;text-align:justify;font-family:{FONT};">{esc(text)}</p>'
    )


def render_lead(items: list[str], p: dict[str, str]) -> str:
    if not items:
        return ""
    content = "".join(
        f'<p style="margin:{"0" if i == len(items)-1 else "0 0 14px 0"};'
        f'color:#343B4F;font-size:16px;line-height:2;letter-spacing:0.04em;'
        f'text-align:justify;font-family:{FONT};">{esc(item)}</p>'
        for i, item in enumerate(items)
    )
    return (
        f'<section style="margin:0 0 26px 0;padding:22px 21px;background:{p["pale"]};'
        f'border-top:3px solid {p["accent"]};border-radius:8px;box-sizing:border-box;">'
        f"{content}</section>"
    )


def render_block(block: dict[str, Any], p: dict[str, str]) -> tuple[str, dict[str, str] | None]:
    kind = str(block.get("type", "")).lower()

    if kind == "paragraph":
        return body_paragraph(str(block.get("text", ""))), None

    if kind == "image":
        uri, digest = image_payload(block)
        alt = esc(block.get("alt", "文章图片"))
        return (
            f'<section style="margin:26px 0 30px 0;padding:0;">'
            f'<img src="{uri}" alt="{alt}" style="display:block;width:100%;height:auto;'
            f'margin:0;border-radius:8px;box-sizing:border-box;" /></section>',
            {"sha256": digest, "alt": str(block.get("alt", ""))},
        )

    if kind == "section":
        number = esc(block.get("number", ""))
        title = esc(block.get("title", ""))
        label = esc(block.get("label") or (f"SECTION {number}" if number else "SECTION"))
        return (
            f'<section style="margin:42px 0 22px 0;text-align:center;">'
            f'<p style="margin:0 0 9px 0;color:{p["accent"]};font-size:12px;line-height:1.4;'
            f'letter-spacing:0.18em;font-weight:700;font-family:{FONT};">{label}</p>'
            f'<h2 style="margin:0;color:#1F2633;font-size:21px;line-height:1.55;'
            f'letter-spacing:0.03em;font-weight:700;font-family:{FONT};">{title}</h2>'
            f'<p style="margin:13px auto 0 auto;width:42px;height:3px;background:{p["accent"]};'
            f'border-radius:3px;line-height:0;font-size:0;">&nbsp;</p></section>',
            None,
        )

    if kind == "callout":
        label = esc(block.get("label", "重点内容"))
        text = esc(block.get("text", ""))
        return (
            f'<section style="margin:0 0 28px 0;padding:22px;background:#FAFAFF;'
            f'border:1px solid #E7E9EF;border-radius:8px;box-sizing:border-box;">'
            f'<p style="margin:0 0 10px 0;color:{p["accent"]};font-size:13px;line-height:1.6;'
            f'letter-spacing:0.12em;font-weight:700;font-family:{FONT};">{label}</p>'
            f'<p style="margin:0;color:#2F3542;font-size:16px;line-height:2;'
            f'letter-spacing:0.04em;text-align:justify;font-family:{FONT};">{text}</p></section>',
            None,
        )

    if kind == "tags":
        items = [str(x) for x in block.get("items", [])]
        pieces: list[str] = []
        for i, item in enumerate(items):
            if i:
                pieces.append(f'<span style="color:#A1A6B3;font-size:13px;">＋</span>')
            pieces.append(
                f'<span style="display:inline-block;margin:4px;padding:5px 10px;'
                f'color:{p["accent"]};font-size:13px;line-height:1.5;background:{p["pale"]};'
                f'border-radius:5px;font-family:{FONT};">{esc(item)}</span>'
            )
        return f'<section style="margin:22px 0 28px 0;text-align:center;line-height:2.5;">{"".join(pieces)}</section>', None

    if kind == "metrics":
        items = list(block.get("items", []))
        columns = []
        width = "47%" if len(items) <= 2 else "31%"
        for item in items:
            columns.append(
                f'<section style="display:inline-block;width:{width};vertical-align:top;'
                f'box-sizing:border-box;margin:5px 0;">'
                f'<p style="margin:0;color:#FFFFFF;font-size:25px;line-height:1.4;'
                f'font-weight:800;font-family:{FONT};">{esc(item.get("value", ""))}</p>'
                f'<p style="margin:4px 0 0 0;color:#CFD5FF;font-size:13px;line-height:1.7;'
                f'font-family:{FONT};">{esc(item.get("label", ""))}</p></section>'
            )
        return (
            f'<section style="margin:22px 0 20px 0;padding:20px 14px;background:{p["dark"]};'
            f'border-radius:8px;box-sizing:border-box;text-align:center;">{"".join(columns)}</section>',
            None,
        )

    if kind == "features":
        items = [esc(x) for x in block.get("items", [])]
        lines = []
        for index in range(0, len(items), 3):
            lines.append(" · ".join(items[index:index + 3]))
        return (
            f'<section style="margin:0 0 26px 0;padding:16px 18px;background:{p["pale"]};'
            f'border-radius:7px;text-align:center;box-sizing:border-box;">'
            f'<p style="margin:0;color:{p["accent"]};font-size:13px;line-height:2;'
            f'letter-spacing:0.04em;font-family:{FONT};">{"<br/>".join(lines)}</p></section>',
            None,
        )

    if kind == "quote":
        label = esc(block.get("label", ""))
        text = esc(block.get("text", ""))
        attribution = esc(block.get("attribution", ""))
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
            f'border-left:4px solid {p["accent"]};border-radius:0 8px 8px 0;'
            f'box-sizing:border-box;">{label_html}'
            f'<p style="margin:0;color:#30364A;font-size:16px;line-height:2;'
            f'letter-spacing:0.04em;text-align:justify;font-family:{FONT};">{text}</p>'
            f'{attribution_html}</section>',
            None,
        )

    if kind == "closing":
        return (
            f'<section style="margin:28px 0 0 0;padding:24px 18px;background:{p["pale"]};'
            f'border-radius:8px;text-align:center;box-sizing:border-box;">'
            f'<p style="margin:0 0 8px 0;color:{p["accent"]};font-size:18px;line-height:1.7;'
            f'font-weight:700;letter-spacing:0.04em;font-family:{FONT};">{esc(block.get("title", ""))}</p>'
            f'<p style="margin:0;color:#656C7D;font-size:14px;line-height:1.9;'
            f'letter-spacing:0.05em;font-family:{FONT};">{esc(block.get("subtitle", ""))}</p></section>',
            None,
        )

    if kind == "signature":
        lines = "".join(
            f'<p style="margin:0;color:#60697A;font-size:14px;line-height:2;'
            f'letter-spacing:0.04em;font-family:{FONT};">{esc(line)}</p>'
            for line in block.get("lines", [])
        )
        date = (
            f'<p style="margin:2px 0 0 0;color:#8A91A3;font-size:13px;line-height:2;'
            f'letter-spacing:0.05em;font-family:{FONT};">{esc(block.get("date"))}</p>'
            if block.get("date") else ""
        )
        return (
            f'<section style="margin:28px 0 0 0;padding:0 2px;text-align:right;'
            f'box-sizing:border-box;">{lines}{date}</section>',
            None,
        )

    raise ValueError(f"Unsupported block type: {kind}")


def render_article(plan: dict[str, Any], palette: dict[str, str]) -> tuple[str, list[dict[str, str]]]:
    label = esc(plan.get("label", "公众号文章"))
    title = esc(plan.get("title", "")).replace("\n", "<br/>")
    subtitle = esc(plan.get("subtitle", ""))
    subtitle_html = (
        f'<p style="margin:16px 0 0 0;color:#8A91A3;font-size:13px;line-height:1.8;'
        f'letter-spacing:0.08em;font-family:{FONT};">{subtitle}</p>'
        if subtitle else ""
    )

    parts = [
        '<section id="wechat-article" style="max-width:677px;margin:0 auto;'
        'padding:34px 20px 44px 20px;background:#FFFFFF;box-sizing:border-box;word-break:break-word;">',
        '<section style="margin:0 0 30px 0;text-align:center;">',
        f'<p style="display:inline-block;margin:0 0 18px 0;padding:6px 13px;'
        f'color:{palette["accent"]};font-size:12px;line-height:1.4;letter-spacing:0.12em;'
        f'font-weight:700;background:{palette["pale"]};border:1px solid #E7E9EF;'
        f'border-radius:20px;font-family:{FONT};">{label}</p>',
        f'<h1 style="margin:0;color:#172033;font-size:28px;line-height:1.45;'
        f'letter-spacing:0.02em;font-weight:800;font-family:{FONT};">{title}</h1>',
        subtitle_html,
        "</section>",
        render_lead([str(x) for x in plan.get("lead", [])], palette),
    ]

    images: list[dict[str, str]] = []
    for block in plan.get("blocks", []):
        rendered, image_info = render_block(block, palette)
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
    palette = merge_palette(plan, theme)
    article, images = render_article(plan, palette)

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
