#!/usr/bin/env python3
"""
Kurumsal duyuru kayıtlarını Gemini ile zenginleştirir (özet + etiket).
"""

import os
import re
import json
import time
import html as html_module
import subprocess
from pathlib import Path
from typing import Any

from google import genai

RAW_FILE   = Path("/root/monitoring/output/institutions_today_raw.json")
OUT_FILE   = Path("/root/monitoring/output/institutions_today_enriched.json")
ERROR_FILE = Path("/root/monitoring/output/institutions_today_enriched_errors.json")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

BATCH_SIZE = 5  # Kurumsal kayıtlar detaylı olduğu için küçük batch


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return default
    return json.loads(text)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def compact_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_tags(tags: Any) -> list:
    if not isinstance(tags, list):
        return []
    clean = []
    for tag in tags:
        t = compact_text(tag)
        if t and t not in clean:
            clean.append(t)
    return clean[:8]


def fallback_summary(item: dict) -> str:
    institution = compact_text(item.get("institution"))
    title       = compact_text(item.get("title"))
    date_text   = compact_text(item.get("date_text"))
    source_type = compact_text(item.get("source_type"))
    parts = [f"{institution} kaydı."]
    if title:
        parts.append(f"Başlık: {title}.")
    if date_text:
        parts.append(f"Tarih: {date_text}.")
    if source_type:
        parts.append(f"Kaynak: {source_type}.")
    if item.get("decision_type"):
        parts.append(f"Karar türü: {compact_text(item['decision_type'])}.")
    if item.get("meeting_no"):
        parts.append(f"Birleşim no: {compact_text(item['meeting_no'])}.")
    if item.get("sections") and isinstance(item["sections"], list):
        parts.append("Bölümler: " + ", ".join(compact_text(s) for s in item["sections"][:5]) + ".")
    return " ".join(parts)


def fallback_tags(item: dict) -> list:
    tags = []
    for key in ["institution", "source_type", "decision_type"]:
        val = compact_text(item.get(key))
        if val and val not in tags:
            tags.append(val)
    if isinstance(item.get("sections"), list):
        for s in item["sections"][:3]:
            sec = compact_text(s)
            if sec and sec not in tags:
                tags.append(sec)
    return tags[:6]


def fetch_page_text(url: str, max_chars: int = 3000) -> str:
    if not url or url.lower().endswith(".pdf"):
        return ""
    try:
        result = subprocess.run(
            ["curl", "-L", "-k", "-A", "Mozilla/5.0", "-s", "--max-time", "12", url],
            capture_output=True, text=True, timeout=17, check=False,
        )
        if result.returncode != 0 or not result.stdout:
            return ""
        text = re.sub(r"<script[^>]*?>.*?</script>", " ", result.stdout, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*?>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html_module.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""


def build_item_context(item: dict) -> str:
    fields = {k: item.get(k) for k in [
        "institution", "source_type", "title", "date_text", "link",
        "decision_no", "decision_type", "source_summary",
        "meeting_no", "time_text", "sections",
    ] if item.get(k)}
    return json.dumps(fields, ensure_ascii=False, indent=2)


def call_gemini_batch(client, items: list) -> list:
    """Bir batch'i Gemini'ye gönderir, her item için {summary, tags} döner."""
    items_text = ""
    for i, item in enumerate(items):
        # body_text varsa kullan, yoksa sayfadan çek
        body_text = compact_text(item.get("body_text", ""))
        SKIP_FETCH = {"TBMM"}
        if not body_text and item.get("institution") not in SKIP_FETCH:
            link = item.get("link", "")
            body_text = fetch_page_text(link)
            if body_text:
                print(f"  [{i}] Sayfa içeriği çekildi ({len(body_text)} karakter)")

        items_text += f"\n[{i}]\n"
        items_text += f"Kurum: {item.get('institution', '')}\n"
        items_text += f"Başlık: {item.get('title', '')}\n"
        items_text += f"Tarih: {item.get('date_text', '')}\n"
        if item.get("decision_no"):
            items_text += f"Karar No: {item['decision_no']}\n"
        if item.get("decision_type"):
            items_text += f"Karar Türü: {item['decision_type']}\n"
        if item.get("source_summary"):
            items_text += f"Kaynak Özet: {item['source_summary']}\n"
        if item.get("sections"):
            items_text += f"Bölümler: {item['sections']}\n"
        if body_text:
            items_text += f"Sayfa İçeriği: {body_text}\n"

    prompt = f"""Aşağıdaki {len(items)} kurumsal duyuru / karar / gündem kaydını analiz et.

Her kayıt için:
1. summary: Türkçe, en fazla 4-5 cümle. Sayfa İçeriği verilmişse ona dayan ve tüm önemli noktaları yakala. Verilmemişse başlık ve metadata'ya dayan. Uydurma ekleme.
2. tags: Türkçe kısa etiketler, en fazla 6 adet.

Kayıtlar:
{items_text}

Yanıtı yalnızca aşağıdaki JSON array formatında ver, başka hiçbir şey ekleme:
[
  {{"index": 0, "summary": "Özet metni.", "tags": ["etiket1", "etiket2"]}},
  {{"index": 1, "summary": "Özet metni.", "tags": ["etiket1"]}},
  ...
]"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            text = response.text.strip()
            if "```" in text:
                parts = text.split("```")
                text = parts[1] if len(parts) > 1 else text
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip().rstrip(",")
            text = re.sub(r',\s*([}\]])', r'\1', text)
            return json.loads(text)
        except Exception as e:
            wait = 15 * (attempt + 1)
            if attempt < 2:
                print(f"  Gemini batch hatası (deneme {attempt+1}/3): {e} — {wait}sn bekleniyor")
                time.sleep(wait)
            else:
                print(f"  Gemini batch 3 denemede başarısız: {e}")
                return []

    return []


def enrich_batch(client, items: list) -> tuple:
    """Batch'i işler, (enriched_list, error_list) döner."""
    enriched = []
    errors   = []

    results = call_gemini_batch(client, items)
    result_map = {r.get("index", -1): r for r in results if isinstance(r, dict)}

    for i, item in enumerate(items):
        enriched_item = dict(item)
        result = result_map.get(i)

        if result:
            summary = compact_text(result.get("summary"))
            tags    = normalize_tags(result.get("tags"))
            enriched_item["summary"]    = summary if summary else fallback_summary(item)
            enriched_item["tags"]       = tags if tags else fallback_tags(item)
            enriched_item["ai_status"]  = "ok"
        else:
            enriched_item["summary"]   = fallback_summary(item)
            enriched_item["tags"]      = fallback_tags(item)
            enriched_item["ai_status"] = "fallback_batch_miss"
            errors.append({
                "title":       item.get("title"),
                "institution": item.get("institution"),
                "error":       "Gemini batch'te bu kayıt için sonuç gelmedi",
            })

        enriched.append(enriched_item)

    return enriched, errors


def main() -> None:
    raw_items = load_json(RAW_FILE, default=[])
    if not isinstance(raw_items, list):
        raise SystemExit("Ham veri JSON listesi değil")

    print(f"Loaded {len(raw_items)} raw records from {RAW_FILE}")

    if not raw_items:
        save_json(OUT_FILE, [])
        save_json(ERROR_FILE, [])
        print("Kayıt yok, çıkılıyor.")
        return

    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY bulunamadı, fallback kullanılıyor.")
        enriched_items = [
            {**item, "summary": fallback_summary(item),
             "tags": fallback_tags(item), "ai_status": "fallback_no_api_key"}
            for item in raw_items
        ]
        save_json(OUT_FILE, enriched_items)
        save_json(ERROR_FILE, [])
        return

    client = genai.Client(api_key=GEMINI_API_KEY)
    all_enriched = []
    all_errors   = []

    for batch_start in range(0, len(raw_items), BATCH_SIZE):
        batch = raw_items[batch_start : batch_start + BATCH_SIZE]
        end   = min(batch_start + BATCH_SIZE, len(raw_items))
        print(f"[{batch_start+1}-{end}/{len(raw_items)}] Gemini'ye gönderiliyor...")

        enriched, errors = enrich_batch(client, batch)
        all_enriched.extend(enriched)
        all_errors.extend(errors)

        if batch_start + BATCH_SIZE < len(raw_items):
            time.sleep(1.0)

    save_json(OUT_FILE, all_enriched)
    save_json(ERROR_FILE, all_errors)

    print(f"Saved {len(all_enriched)} enriched records to {OUT_FILE}")
    print(f"Saved {len(all_errors)} error records to {ERROR_FILE}")


if __name__ == "__main__":
    main()
