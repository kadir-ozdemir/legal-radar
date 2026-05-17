#!/usr/bin/env python3
"""
Günlük Sektörel Haber Özeti Pipeline
RSS kaynaklarından haber çeker, Gemini ile sınıflandırır/özetler, mail gönderir.
"""

import os
import re
import sys
import time
import logging
import smtplib
import hashlib
import json
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from pathlib import Path as _Path

def _load_news_config():
    config_file = _Path("/root/monitoring/panel/config.json")
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            news = data.get("news", {})
            sectors_raw = news.get("sectors", {})
            if sectors_raw:
                sectors = {n: d.get("keywords", []) for n, d in sectors_raw.items()}
                colors   = {n: d.get("color", "#555555") for n, d in sectors_raw.items()}
            else:
                sectors, colors = None, None
            rss = news.get("rss_feeds", {}) or None
            return sectors, colors, rss
        except Exception:
            pass
    return None, None, None


import feedparser
from google import genai

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
SMTP_HOST      = os.environ["RG_SMTP_HOST"]
SMTP_PORT      = int(os.environ.get("RG_SMTP_PORT", "587"))
SMTP_USER      = os.environ["RG_SMTP_USER"]
SMTP_PASS      = os.environ["RG_SMTP_APP_PASSWORD"]
MAIL_FROM      = os.environ.get("RG_MAIL_FROM", SMTP_USER)
MAIL_TO        = os.environ.get("NEWS_MAIL_TO", os.environ.get("INSTITUTIONS_MAIL_TO", ""))

SCRIPT_DIR = Path(__file__).parent
SENT_LOG   = SCRIPT_DIR / "sent_hashes.json"

RSS_FEEDS = {
    "Bloomberg HT":            "https://www.bloomberght.com/rss",
    "Dünya Gazetesi":          "https://www.dunya.com/rss",
    "Ekonomim":                "https://www.ekonomim.com/rss",
    "Para Analiz":             "https://www.paraanaliz.com/feed",
    "Sabah Ekonomi":           "https://www.sabah.com.tr/rss/ekonomi.xml",
    "Patronlar Dünyası Ekonomi":  "https://www.patronlardunyasi.com/rss/ekonomi",
    "Patronlar Dünyası Finans":   "https://www.patronlardunyasi.com/rss/finans",
    "Patronlar Dünyası Teknoloji":"https://www.patronlardunyasi.com/rss/teknoloji",
}

SECTORS = {
    "Bahis": [
        "bahis", "iddaa", "kumar", "şans oyunu", "spor bahis",
        "illegal bahis", "yasadışı bahis", "canlı bahis", "lisanslı bahis",
    ],
    "İnşaat": [
        "inşaat", "yapı", "konut", "gayrimenkul", "müteahhit",
        "toki", "kentsel dönüşüm", "bina", "arsa",
    ],
    "Yazılım": [
        "yazılım", "teknoloji", "yapay zeka", " ai ", "uygulama",
        "startup", "dijital", "siber", "veri", "bulut", "saas", "fintech",
    ],
    "Yeme & İçme": [
        "restoran", "gıda", "içecek", "fast food", "café", "kafe",
        "zincir", "franchise", "yemek",
    ],
    "Enerji": [
        "enerji", "elektrik", "doğalgaz", "yenilenebilir", "petrol",
        "güneş", "rüzgar", "nükleer", "epdk", "botaş", "akaryakıt",
    ],
}

SECTOR_COLORS = {
    "Bahis":       "#e74c3c",
    "İnşaat":      "#e67e22",
    "Yazılım":     "#3498db",
    "Yeme & İçme": "#27ae60",
    "Enerji":      "#8e44ad",
}

# ── Duplicate Prevention ──────────────────────────────────────────────────────

def load_sent_hashes() -> set:
    if not SENT_LOG.exists():
        return set()
    data = json.loads(SENT_LOG.read_text(encoding="utf-8"))
    today = datetime.now().strftime("%Y-%m-%d")
    return set(data.get(today, []))


def save_sent_hashes(hashes: set):
    today = datetime.now().strftime("%Y-%m-%d")
    data: dict = {}
    if SENT_LOG.exists():
        data = json.loads(SENT_LOG.read_text(encoding="utf-8"))
    data[today] = list(hashes)
    # 7 günden eskiyi temizle
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    data = {k: v for k, v in data.items() if k >= cutoff}
    SENT_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def article_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

# ── RSS Helpers ───────────────────────────────────────────────────────────────

def is_recent(entry: dict) -> bool:
    try:
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if not published:
            return True
        pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        return pub_dt.date() == yesterday
    except Exception:
        return True


def keyword_match(text: str, keywords: list) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def fetch_candidates() -> list:
    all_keywords = [kw for kws in SECTORS.values() for kw in kws]
    candidates = []

    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if not is_recent(entry):
                    continue
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                link    = entry.get("link", "").strip()
                if not title or not link:
                    continue
                if keyword_match(f"{title} {summary}", all_keywords):
                    candidates.append({
                        "source":  source,
                        "title":   title,
                        "url":     link,
                        "summary": summary[:400],
                    })
                    count += 1
            log.info(f"{source}: {len(feed.entries)} haber tarandı, {count} aday")
        except Exception as e:
            log.warning(f"{source} RSS okunamadı: {e}")

    log.info(f"Toplam {len(candidates)} aday haber (keyword filtresi sonrası)")
    return candidates

# ── Gemini ────────────────────────────────────────────────────────────────────

def gemini_classify_and_summarize(articles: list) -> list:
    client = genai.Client(api_key=GEMINI_API_KEY)

    results = []
    batch_size = 10

    for batch_start in range(0, len(articles), batch_size):
        batch = articles[batch_start : batch_start + batch_size]

        articles_text = ""
        for i, art in enumerate(batch):
            articles_text += f"\n[{i}] Başlık: {art['title']}\nÖzet: {art['summary'][:300]}\n"

        prompt = f"""Aşağıdaki {len(batch)} haberi analiz et.

Her haber için:
1. Şu sektörlerden hangisine(lerine) giriyor: Bahis, İnşaat, Yazılım, Yeme & İçme, Enerji
2. Hiçbirine girmiyorsa sektorler alanını boş bırak.
3. İlgiliyse haberi Türkçe 2 cümleyle özetle.

Haberler:
{articles_text}

Yanıtı yalnızca aşağıdaki JSON array formatında ver, başka hiçbir şey ekleme:
[
  {{"index": 0, "sektorler": ["Yazılım"], "ozet": "Özet metni."}},
  {{"index": 1, "sektorler": [], "ozet": ""}},
  ...
]"""

        for attempt in range(3):
            try:
                response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                text = response.text.strip()
                # Markdown kod bloğu varsa temizle
                if "```" in text:
                    parts = text.split("```")
                    text = parts[1] if len(parts) > 1 else text
                    if text.startswith("json"):
                        text = text[4:]
                # Trailing comma gibi yaygın JSON hatalarını düzelt
                text = text.strip().rstrip(",")
                text = re.sub(r',\s*([}\]])', r'\1', text)
                parsed = json.loads(text)
                for item in parsed:
                    idx     = item.get("index", -1)
                    sectors = item.get("sektorler", [])
                    if not isinstance(sectors, list):
                        sectors = []
                    if sectors and 0 <= idx < len(batch):
                        results.append({
                            **batch[idx],
                            "sectors":    sectors,
                            "ai_summary": item.get("ozet", "").strip(),
                        })
                break  # başarılı, döngüden çık
            except Exception as e:
                wait = 15 * (attempt + 1)
                if attempt < 2:
                    log.warning(f"Gemini batch hatası (batch {batch_start}, deneme {attempt+1}/3): {e} — {wait}sn bekleniyor")
                    time.sleep(wait)
                else:
                    log.warning(f"Gemini batch hatası (batch {batch_start}), 3 denemede de başarısız: {e}")

    log.info(f"Gemini sonrası {len(results)} ilgili haber")
    return results

# ── Email ─────────────────────────────────────────────────────────────────────

def build_html(articles: list) -> str:
    today_str = datetime.now().strftime("%d.%m.%Y")

    # Sektöre göre grupla (bir haber birden fazla sektörde çıkabilir)
    by_sector: dict = {s: [] for s in SECTORS}
    for art in articles:
        for sector in art.get("sectors", []):
            if sector in by_sector:
                by_sector[sector].append(art)

    active_sectors = {k: v for k, v in by_sector.items() if v}
    if not active_sectors:
        return ""

    sections_html = ""
    for sector, arts in active_sectors.items():
        color = SECTOR_COLORS.get(sector, "#555555")
        items_html = ""
        for art in arts:
            items_html += f"""
            <div style="margin-bottom:16px; padding:14px 16px; background:#fafafa;
                        border-left:4px solid {color}; border-radius:4px;">
              <a href="{art['url']}"
                 style="font-size:14px; font-weight:bold; color:#1a1a2e; text-decoration:none; line-height:1.4;">
                {art['title']}
              </a>
              <p style="margin:8px 0 6px 0; color:#444; font-size:13px; line-height:1.6;">
                {art['ai_summary']}
              </p>
              <span style="font-size:11px; color:#999;">📰 {art['source']}</span>
            </div>"""

        sections_html += f"""
        <div style="margin-bottom:28px;">
          <h2 style="color:{color}; border-bottom:2px solid {color}; padding-bottom:6px;
                     font-size:15px; margin-bottom:14px;">
            {sector}
            <span style="font-size:12px; color:#999; font-weight:normal;">
              — {len(arts)} haber
            </span>
          </h2>
          {items_html}
        </div>"""

    total = sum(len(v) for v in active_sectors.values())
    sources_str = ", ".join(RSS_FEEDS.keys())

    return f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif; max-width:680px; margin:auto; padding:20px; color:#333; background:#fff;">

  <div style="background:#1a1a2e; color:white; padding:20px 24px; border-radius:8px; margin-bottom:24px;">
    <h1 style="margin:0; font-size:19px; letter-spacing:0.3px;">📊 Günlük Sektörel Haber Özeti</h1>
    <p style="margin:6px 0 0 0; color:#aab; font-size:12px;">
      {today_str} &nbsp;·&nbsp; {total} haber &nbsp;·&nbsp; {len(active_sectors)} sektör
    </p>
  </div>

  {sections_html}

  <div style="margin-top:28px; padding:12px 16px; background:#f4f4f4; border-radius:6px;
              font-size:11px; color:#999; text-align:center; line-height:1.6;">
    Bu e-posta otomatik olarak oluşturulmuştur.<br>
    Kaynaklar: {sources_str}
  </div>

</body></html>"""


def send_mail(html: str):
    today_str = datetime.now().strftime("%d.%m.%Y")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Günlük Sektörel Haber Özeti – {today_str}"
    msg["From"]    = MAIL_FROM
    msg["To"]      = MAIL_TO
    msg.attach(MIMEText(html, "html", "utf-8"))

    recipients = [r.strip() for r in MAIL_TO.split(",")]
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(MAIL_FROM, recipients, msg.as_string())
    log.info(f"Mail gönderildi → {MAIL_TO}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    log.info(f"=== Günlük Sektörel Haber Pipeline başladı — {today} ===")

    sent_hashes = load_sent_hashes()

    # 1. RSS'ten aday haberleri çek (keyword filtresi)
    candidates = fetch_candidates()
    if not candidates:
        log.info("Aday haber bulunamadı. Çıkılıyor.")
        return

    # 2. Bugün gönderilmiş URL'leri çıkar
    new_candidates = [a for a in candidates if article_hash(a["url"]) not in sent_hashes]
    log.info(f"{len(new_candidates)} yeni haber Gemini'ye gönderilecek")
    if not new_candidates:
        log.info("Tüm haberler zaten işlenmiş. Çıkılıyor.")
        return

    # 3. Gemini ile sınıflandır ve özetle
    articles = gemini_classify_and_summarize(new_candidates)
    if not articles:
        log.info("İlgili haber bulunamadı. Mail gönderilmeyecek.")
        return

    # 4. HTML oluştur ve gönder
    html = build_html(articles)
    if not html:
        log.info("Gösterilecek içerik yok. Mail gönderilmeyecek.")
        return

    send_mail(html)

    # 5. Gönderilen hash'leri kaydet (duplicate önleme)
    new_hashes = {article_hash(a["url"]) for a in new_candidates}
    save_sent_hashes(sent_hashes | new_hashes)

    log.info("=== Pipeline tamamlandı ===")


if __name__ == "__main__":
    main()
