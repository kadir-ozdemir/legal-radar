#!/usr/bin/env python3
"""
Resmî Gazete içeriğini çeker ve modern HTML mail şablonu oluşturur.
"""

import re
import html
import urllib.request
from datetime import datetime

URL = "https://www.resmigazete.gov.tr/"
UA  = "Mozilla/5.0"

MONTHS_TR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
    5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
    9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık",
}

SECTION_COLORS = {
    "YÜRÜTME VE İDARE BÖLÜMÜ": "#1a5276",
    "İLÂN BÖLÜMÜ":             "#784212",
    "YARGI BÖLÜMÜ":            "#1e8449",
}
DEFAULT_SECTION_COLOR = "#2c3e50"

today      = datetime.now()
yyyy       = today.strftime("%Y")
mm         = today.strftime("%m")
yyyymmdd   = today.strftime("%Y%m%d")
display_date = today.strftime("%d.%m.%Y")
title_date   = f"{today.day} {MONTHS_TR[today.month]} {today.year}"

# ── Sayfa çek ────────────────────────────────────────────────────────────────
req = urllib.request.Request(URL, headers={"User-Agent": UA})
raw = urllib.request.urlopen(req).read().decode("utf-8", errors="ignore")

patterns = [
    f"/eskiler/{yyyy}/{mm}/{yyyymmdd}",
    f"/ilanlar/eskiilanlar/{yyyy}/{mm}/{yyyymmdd}",
]

# ── Metin temizle ─────────────────────────────────────────────────────────────
def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value

# ── İçeriği ayrıştır ─────────────────────────────────────────────────────────
token_pattern = re.compile(
    r'(<div class="card-title html-title"[^>]*>.*?</div>)'
    r'|(<div class="html-subtitle"[^>]*>.*?</div>)'
    r'|(<div class="fihrist-item mb-1">\s*<a href="https://www\.resmigazete\.gov\.tr/[^"]+"[^>]*>.*?</a>\s*</div>)',
    re.I | re.S
)

link_pattern = re.compile(
    r'<a href="(https://www\.resmigazete\.gov\.tr/[^"]+)"[^>]*>(.*?)</a>',
    re.I | re.S
)

sections         = []
current_section  = None
current_subtitle = None

for match in token_pattern.finditer(raw):
    token = match.group(0)

    if 'card-title html-title' in token:
        title = clean_text(token)
        current_section = {"title": title, "groups": []}
        sections.append(current_section)
        current_subtitle = None
        continue

    if 'html-subtitle' in token:
        subtitle = clean_text(token)
        if current_section is None:
            current_section = {"title": "", "groups": []}
            sections.append(current_section)
        current_subtitle = {"subtitle": subtitle, "items": []}
        current_section["groups"].append(current_subtitle)
        continue

    link_match = link_pattern.search(token)
    if not link_match:
        continue

    href, text = link_match.groups()
    if not any(p in href for p in patterns):
        continue

    clean = clean_text(text)
    if not clean:
        continue

    if current_section is None:
        current_section = {"title": "", "groups": []}
        sections.append(current_section)

    if current_subtitle is None:
        current_subtitle = {"subtitle": "", "items": []}
        current_section["groups"].append(current_subtitle)

    current_subtitle["items"].append((clean, href))

# Boş bölümleri temizle
filtered_sections = []
for section in sections:
    groups = [g for g in section["groups"] if g["items"]]
    if groups:
        filtered_sections.append({"title": section["title"], "groups": groups})

total_items = sum(
    len(g["items"])
    for s in filtered_sections
    for g in s["groups"]
)

# ── HTML oluştur ──────────────────────────────────────────────────────────────
out = []
out.append(f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif; max-width:680px; margin:auto;
                   padding:20px; color:#333; background:#fff;">

  <div style="background:#1a1a2e; color:white; padding:20px 24px;
              border-radius:8px; margin-bottom:24px;">
    <h1 style="margin:0; font-size:19px; letter-spacing:0.3px;">
      📋 Resmî Gazete
    </h1>
    <p style="margin:6px 0 0 0; color:#aab; font-size:12px;">
      {title_date} &nbsp;·&nbsp; {total_items} madde &nbsp;·&nbsp; {len(filtered_sections)} bölüm
    </p>
  </div>""")

if not filtered_sections:
    out.append("<p style='color:#666;'>Bugün Resmî Gazete'de içerik bulunamadı.</p>")
else:
    for section in filtered_sections:
        color = SECTION_COLORS.get(section["title"], DEFAULT_SECTION_COLOR)

        out.append(f"""
  <div style="margin-bottom:28px;">
    <h2 style="color:{color}; border-bottom:2px solid {color};
               padding-bottom:6px; font-size:15px; margin-bottom:16px;">
      {html.escape(section["title"])}
    </h2>""")

        for group in section["groups"]:
            if group["subtitle"]:
                out.append(f"""
    <h3 style="font-size:13px; color:#555; font-weight:bold;
               margin:16px 0 8px 0; text-transform:uppercase;
               letter-spacing:0.4px;">
      {html.escape(group["subtitle"])}
    </h3>""")

            for text, href in group["items"]:
                # Baştaki tire/dash işaretini temizle
                display = re.sub(r'^[—–\-‒]+\s*', '', text).strip()
                out.append(f"""
    <div style="padding:8px 12px 8px 16px; margin-bottom:4px;
                border-left:3px solid {color}; background:#fafafa; border-radius:3px;">
      <a href="{html.escape(href)}"
         style="color:#1a1a2e; font-size:13px; text-decoration:none; line-height:1.5;">
        {html.escape(display)}
      </a>
    </div>""")

        out.append("  </div>")

out.append(f"""
  <div style="margin-top:28px; padding:12px 16px; background:#f4f4f4;
              border-radius:6px; font-size:11px; color:#999;
              text-align:center; line-height:1.6;">
    Bu e-posta otomatik olarak oluşturulmuştur.<br>
    Kaynak: <a href="{URL}" style="color:#999;">resmigazete.gov.tr</a>
  </div>

</body></html>""")

print("\n".join(out))
