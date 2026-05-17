#!/usr/bin/env python3
"""
Kurumsal duyuru verilerinden HTML mail önizlemesi oluşturur.
"""

import json
import html
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import os

ENRICHED_FILE = Path("/root/monitoring/output/institutions_today_enriched.json")
OUT_FILE      = Path("/root/monitoring/output/institutions_today_preview.html")

INSTITUTION_COLORS = {
    "SPK":                    "#1a5276",
    "BDDK":                   "#1e8449",
    "Ticaret Bakanlığı":      "#784212",
    "EPDK":                   "#6c3483",
    "Rekabet Kurumu":         "#c0392b",
    "İstanbul Ticaret Odası": "#d35400",
    "TBMM":                   "#2e4057",
}
DEFAULT_COLOR = "#555555"

TBMM_SOURCE_LABELS = {
    "genel_kurul_gundemi": "TBMM Genel Kurul Gündemi",
    "komisyon_gundemleri": "TBMM Komisyon Gündemleri",
}

SOURCE_LABELS = {
    "bulletins":             "Bültenler",
    "announcements":         "Duyurular",
    "genel_kurul_gundemi":   "Genel Kurul Gündemi",
    "komisyon_gundemleri":   "Komisyon Gündemleri",
}

SECTION_ORDER = [
    "SPK", "BDDK", "EPDK", "Rekabet Kurumu",
    "Ticaret Bakanlığı", "İstanbul Ticaret Odası",
    "TBMM Genel Kurul Gündemi", "TBMM Komisyon Gündemleri",
]


def load_json(path: Path):
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def esc(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def compact_tags(tags) -> list:
    if not isinstance(tags, list):
        return []
    out = []
    for tag in tags:
        t = str(tag).strip()
        if t and t not in out:
            out.append(t)
    return out[:8]


def get_section_title(item: dict) -> str:
    institution = str(item.get("institution", "")).strip()
    source_type = str(item.get("source_type", "")).strip()
    if institution == "TBMM":
        return TBMM_SOURCE_LABELS.get(source_type, "TBMM")
    return institution


def get_institution_color(section_title: str) -> str:
    for key, color in INSTITUTION_COLORS.items():
        if key in section_title:
            return color
    return DEFAULT_COLOR


def get_source_label(item: dict) -> str:
    source_type = str(item.get("source_type", "")).strip()
    return SOURCE_LABELS.get(source_type, source_type)


def build_record_html(item: dict, color: str) -> str:
    title      = esc(item.get("title", ""))
    date_text  = esc(item.get("date_text", ""))
    summary    = esc(item.get("summary", ""))
    link       = esc(item.get("link", ""))
    source_lbl = esc(get_source_label(item))
    tags       = compact_tags(item.get("tags", []))

    meta_parts = []
    if source_lbl:
        meta_parts.append(source_lbl)
    if date_text:
        meta_parts.append(date_text)
    if item.get("meeting_no"):
        meta_parts.append(f"Birleşim No: {esc(item['meeting_no'])}")
    if item.get("time_text"):
        meta_parts.append(f"Saat: {esc(item['time_text'])}")

    meta_html = ""
    if meta_parts:
        meta_html = (
            "<div style='color:#666; font-size:12px; margin-top:4px;'>"
            + " &nbsp;·&nbsp; ".join(meta_parts)
            + "</div>"
        )

    tags_html = ""
    if tags:
        tag_spans = "".join(
            f"<span style='display:inline-block; background:#f1f3f5; border:1px solid #ddd; "
            f"border-radius:12px; padding:2px 8px; margin:3px 4px 0 0; font-size:11px; color:#444;'>"
            f"{esc(tag)}</span>"
            for tag in tags
        )
        tags_html = f"<div style='margin-top:8px;'>{tag_spans}</div>"

    link_html = ""
    if link:
        link_html = (
            f"<div style='margin-top:10px;'>"
            f"<a href='{link}' style='color:{color}; font-size:12px; text-decoration:none;'>"
            f"&#8599; Kaynağa git</a></div>"
        )

    return f"""
    <div style="margin-bottom:18px; padding:14px 16px; background:#fafafa;
                border-left:4px solid {color}; border-radius:4px;">
      <div style="font-weight:700; color:#111; font-size:14px; line-height:1.4;">{title}</div>
      {meta_html}
      <div style="margin-top:8px; color:#333; font-size:13px; line-height:1.6;">{summary}</div>
      {tags_html}
      {link_html}
    </div>"""


def sort_sections(sections: list) -> list:
    order_map = {name: i for i, name in enumerate(SECTION_ORDER)}
    return sorted(sections, key=lambda s: order_map.get(s[0], 99))


def main():
    items = load_json(ENRICHED_FILE)

    grouped: dict = defaultdict(list)
    for item in items:
        if not isinstance(item, dict):
            continue
        grouped[get_section_title(item)].append(item)

    non_empty = [(s, r) for s, r in grouped.items() if r]
    non_empty = sort_sections(non_empty)

    target_date = os.getenv("TARGET_DATE", "").strip()
    if target_date:
        dt = datetime.strptime(target_date, "%Y-%m-%d")
    else:
        dt = datetime.now()
    date_str = dt.strftime("%d.%m.%Y")

    total = sum(len(r) for _, r in non_empty)

    parts = [f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif; max-width:680px; margin:auto;
                   padding:20px; color:#333; background:#fff;">

  <div style="background:#1a1a2e; color:white; padding:20px 24px;
              border-radius:8px; margin-bottom:24px;">
    <h1 style="margin:0; font-size:19px; letter-spacing:0.3px;">
      🏛 Günlük Kurumsal Duyuru Özeti
    </h1>
    <p style="margin:6px 0 0 0; color:#aab; font-size:12px;">
      {date_str} &nbsp;·&nbsp; {total} kayıt &nbsp;·&nbsp; {len(non_empty)} kurum
    </p>
  </div>"""]

    if not non_empty:
        parts.append(
            "<p style='color:#666;'>Bugün takip ettiğimiz kurumların resmi web sitelerinde "
            "yeni duyuru yapılmadı.</p>"
        )
    else:
        for section, records in non_empty:
            color = get_institution_color(section)
            records_html = "".join(build_record_html(item, color) for item in records)
            parts.append(f"""
  <div style="margin-bottom:28px;">
    <h2 style="color:{color}; border-bottom:2px solid {color}; padding-bottom:6px;
               font-size:15px; margin-bottom:14px;">
      {esc(section)}
      <span style="font-size:12px; color:#999; font-weight:normal;">
        — {len(records)} kayıt
      </span>
    </h2>
    {records_html}
  </div>""")

    parts.append(f"""
  <div style="margin-top:28px; padding:12px 16px; background:#f4f4f4; border-radius:6px;
              font-size:11px; color:#999; text-align:center; line-height:1.6;">
    Bu e-posta otomatik olarak oluşturulmuştur.<br>
    Kaynaklar: SPK · BDDK · EPDK · Rekabet Kurumu · Ticaret Bakanlığı · İTO · TBMM
  </div>

</body></html>""")

    OUT_FILE.write_text("".join(parts), encoding="utf-8")
    print(f"HTML önizleme kaydedildi: {OUT_FILE} ({total} kayıt)")


if __name__ == "__main__":
    main()
