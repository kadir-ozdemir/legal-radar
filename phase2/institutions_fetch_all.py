import os
import re
import html
import json
import subprocess
from datetime import datetime
from urllib.parse import urljoin
from pathlib import Path

OUTPUT_FILE = "/root/monitoring/output/institutions_today_raw.json"
USER_AGENT = "Mozilla/5.0"

MONTHS_TR = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık",
}

def get_target_datetime():
    target_date = os.getenv("TARGET_DATE", "").strip()
    if target_date:
        return datetime.strptime(target_date, "%Y-%m-%d")
    return datetime.now()


today = get_target_datetime()
today_spk_str = f"{today.day} {MONTHS_TR[today.month]} {today.year}"
today_bddk_str = today.strftime("%d.%m.%Y")


def fetch_url(url: str, insecure: bool = False) -> str:
    cmd = ["curl"]
    if insecure:
        cmd.append("-k")
    cmd += ["-L", "-A", USER_AGENT, "-s", url]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {url} with code {result.returncode}")

    return result.stdout


def parse_spk_today():
    url = "https://spk.gov.tr/spk-bultenleri/2026-yili-spk-bultenleri"
    page = fetch_url(url, insecure=True)

    pattern = re.compile(
        r'<a href="(?P<link>https://spk\.gov\.tr/data/[^"]+\.pdf)" class="link">\s*'
        r'<div class="liste-item">.*?'
        r'<div class="liste-baslik">\s*(?P<title>.*?)\s*</div>.*?'
        r'<div class="liste-icerik[^"]*">\s*(?P<date_text>.*?)\s*</div>',
        re.I | re.S,
    )

    records = []
    for link, title, date_text in pattern.findall(page):
        clean_title = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
        clean_date = html.unescape(re.sub(r"<[^>]+>", "", date_text)).strip()

        record = {
            "institution": "SPK",
            "source_type": "bulletins",
            "title": clean_title,
            "date_text": clean_date,
            "link": link,
        }

        if today_spk_str in clean_date:
            records.append(record)

    return records


def parse_bddk_today():
    url = "https://www.bddk.org.tr/Duyuru/Liste"
    base = "https://www.bddk.org.tr"
    page = fetch_url(url, insecure=True)

    pattern = re.compile(
        r'<a href="(?P<href>/Duyuru/Detay/\d+)">.*?'
        r'<span class="gorunenTarih">(?P<date>.*?)</span>\s*'
        r'(?P<title>.*?)\s*'
        r'</span>',
        re.I | re.S,
    )

    records = []
    for href, date_text, title in pattern.findall(page)[:20]:
        clean_title = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
        clean_date = html.unescape(re.sub(r"<[^>]+>", "", date_text)).strip()
        full_url = urljoin(base, href)

        record = {
            "institution": "BDDK",
            "source_type": "announcements",
            "title": clean_title,
            "date_text": clean_date,
            "link": full_url,
        }

        if clean_date == today_bddk_str:
            records.append(record)

    return records

def parse_ticaret_today():
    url = "https://ticaret.gov.tr/duyurular"
    base = "https://ticaret.gov.tr"
    page = fetch_url(url, insecure=True)

    pattern = re.compile(
        r'<li>\s*<a href="(?P<href>/duyurular/[^"]+|https://tagm\.ticaret\.gov\.tr/[^"]+|https://personel\.ticaret\.gov\.tr/[^"]+)">.*?<h5>(?P<title>.*?)</h5>',
        re.I | re.S,
    )

    records = []
    for href, title in pattern.findall(page)[:20]:
        clean_title = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
        full_url = urljoin(base, href)

        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', clean_title)
        extracted_date = date_match.group(1) if date_match else ""

        record = {
            "institution": "Ticaret Bakanlığı",
            "source_type": "announcements",
            "title": clean_title,
            "date_text": extracted_date,
            "link": full_url,
        }

        if extracted_date == today_bddk_str:
            records.append(record)

    return records

def parse_epdk_today():
    url = "https://www.epdk.gov.tr/detay/icerik/4-0-1/duyurular"
    base = "https://www.epdk.gov.tr"
    page = fetch_url(url, insecure=False)

    pattern = re.compile(
        r'<tr class="text-liste">.*?'
        r'<th class="hidden-xs">(?P<date>.*?)</th>.*?'
        r"<td><a href='(?P<href>/Detay/Icerik/[^']+)'[^>]*>(?P<title>.*?)</a></td>",
        re.I | re.S,
    )

    records = []
    for date_text, href, title in pattern.findall(page):
        clean_date = html.unescape(re.sub(r"<[^>]+>", "", date_text)).strip()
        clean_title = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
        full_url = urljoin(base, href)

        if clean_date == today_bddk_str:
            records.append({
                "institution": "EPDK",
                "source_type": "announcements",
                "title": clean_title,
                "date_text": clean_date,
                "link": full_url,
            })

    return records


def parse_rekabet_today():
    url = "https://www.rekabet.gov.tr/tr/SonkurulKararlari"
    base = "https://www.rekabet.gov.tr"
    page = fetch_url(url, insecure=False)

    today_rekabet_str = f"{today.day}.{today.month}.{today.year}"

    pattern = re.compile(
        r'<a href="(?P<href>/tr/SonKurulKarari/[^"]+)"[^>]*>.*?'
        r'Karar Sayısı\s*:\s*(?P<decision_no>.*?)</td>.*?'
        r'Karar Tarihi\s*:\s*(?P<date>.*?)</td>.*?'
        r'Karar Türü\s*:\s*(?P<decision_type>.*?)</td>.*?'
        r'<td colspan="3" class="tablotitle">(?P<title>.*?)</td>.*?'
        r'<td colspan="3">(?P<source_summary>.*?)</td>.*?'
        r'</a>',
        re.I | re.S,
    )

    records = []
    for href, decision_no, date_text, decision_type, title, source_summary in pattern.findall(page):
        clean_date = html.unescape(re.sub(r"<[^>]+>", "", date_text)).strip()
        clean_title = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
        clean_decision_no = html.unescape(re.sub(r"<[^>]+>", "", decision_no)).strip()
        clean_decision_type = html.unescape(re.sub(r"<[^>]+>", "", decision_type)).strip()
        clean_source_summary = html.unescape(re.sub(r"<[^>]+>", "", source_summary)).strip()
        full_url = urljoin(base, href)

        if clean_date == today_rekabet_str:
            records.append({
                "institution": "Rekabet Kurumu",
                "source_type": "board_decisions",
                "title": clean_title,
                "date_text": clean_date,
                "link": full_url,
                "decision_no": clean_decision_no,
                "decision_type": clean_decision_type,
                "source_summary": clean_source_summary,
            })

    return records


def parse_ito_today():
    url = "https://www.ito.org.tr/tr/duyurular"
    base = "https://www.ito.org.tr"
    page = fetch_url(url, insecure=False)

    months_tr = {
        "Ocak": 1,
        "Şubat": 2,
        "Mart": 3,
        "Nisan": 4,
        "Mayıs": 5,
        "Haziran": 6,
        "Temmuz": 7,
        "Ağustos": 8,
        "Eylül": 9,
        "Ekim": 10,
        "Kasım": 11,
        "Aralık": 12,
    }

    pattern = re.compile(
        r'<a href="(?P<href>/tr/duyurular/detay/[^"]+)" class="announcements-box">.*?'
        r'<time>(?P<date_text>.*?)</time>.*?'
        r'<h4>(?P<title>.*?)</h4>',
        re.I | re.S,
    )

    def normalize_ito_date(date_text: str) -> str:
        clean = html.unescape(re.sub(r"<[^>]+>", "", date_text)).strip()
        parts = clean.split()
        if len(parts) != 3:
            return ""
        day = int(parts[0])
        month_name = parts[1]
        year = int(parts[2])
        month = months_tr.get(month_name)
        if not month:
            return ""
        return f"{day}.{month}.{year}"

    today_ito_str = f"{today.day}.{today.month}.{today.year}"

    records = []
    for href, date_text, title in pattern.findall(page):
        clean_title = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
        normalized_date = normalize_ito_date(date_text)
        full_url = urljoin(base, href)

        if normalized_date == today_ito_str:
            records.append({
                "institution": "İstanbul Ticaret Odası",
                "source_type": "announcements",
                "title": clean_title,
                "date_text": normalized_date,
                "link": full_url,
            })

    return records


def parse_tbmm_genel_kurul_today():
    url = "https://www.tbmm.gov.tr/Gundem/GenelKurulGundemi"
    page = fetch_url(url, insecure=False)

    months_tr = {
        "OCAK": 1,
        "ŞUBAT": 2,
        "MART": 3,
        "NİSAN": 4,
        "MAYIS": 5,
        "HAZİRAN": 6,
        "TEMMUZ": 7,
        "AĞUSTOS": 8,
        "EYLÜL": 9,
        "EKİM": 10,
        "KASIM": 11,
        "ARALIK": 12,
    }

    iframe_match = re.search(r'<iframe[^>]*src="(.*?)"[^>]*></iframe>', page, re.I | re.S)
    if not iframe_match:
        return []

    raw_iframe = iframe_match.group(1)
    decoded = html.unescape(raw_iframe)

    def clean_text(s: str) -> str:
        s = re.sub(r"<[^>]+>", " ", s)
        s = html.unescape(s)
        s = s.replace("\r", " ").replace("\n", " ")
        s = re.sub(r"\s+", " ", s).strip()
        return s

    clean = clean_text(decoded)

    birlesim_match = re.search(r"(\d+)[’']?NCI BİRLEŞİM", clean, re.I)
    date_match = re.search(r"(\d{1,2})\s+([A-ZÇĞİÖŞÜ]+)\s+(\d{4})", clean, re.I)
    time_match = re.search(r"SAAT:\s*([0-9]{1,2}\.[0-9]{2})", clean, re.I)

    birlesim_no = birlesim_match.group(1) if birlesim_match else ""
    normalized_date = ""

    if date_match:
        day = int(date_match.group(1))
        month_name = date_match.group(2).upper()
        year = int(date_match.group(3))
        month = months_tr.get(month_name)
        if month:
            normalized_date = f"{day}.{month}.{year}"

    time_text = time_match.group(1) if time_match else ""

    section_titles = re.findall(
        r"(BAŞKANLIĞIN GENEL KURULA SUNUŞLARI|ÖZEL GÜNDEMDE YER ALACAK İŞLER|SEÇİM|OYLAMASI YAPILACAK İŞLER|MECLİS SORUŞTURMASI RAPORLARI|GENEL GÖRÜŞME VE MECLİS ARAŞTIRMASI YAPILMASINA DAİR ÖNGÖRÜŞMELER|KANUN TEKLİFLERİ İLE KOMİSYONLARDAN GELEN DİĞER İŞLER)",
        clean,
        re.I
    )
    section_titles = list(dict.fromkeys([s.strip() for s in section_titles]))

    today_tbmm_str = f"{today.day}.{today.month}.{today.year}"

    records = []
    if normalized_date == today_tbmm_str:
        records.append({
            "institution": "TBMM",
            "source_type": "genel_kurul_gundemi",
            "title": f"Genel Kurul Gündemi - {birlesim_no}. Birleşim",
            "date_text": normalized_date,
            "meeting_no": birlesim_no,
            "time_text": time_text,
            "link": url,
            "sections": section_titles,
        })

    return records

def parse_tbmm_komisyon_today():
    url = "https://www.tbmm.gov.tr/Gundem/KomisyonGundemleri"
    page = fetch_url(url, insecure=False)

    if "EKLENMİŞ KOMİSYON GÜNDEMLERİ BULUNMAMAKTADIR" in page:
        return []

    table_match = re.search(
        r'<table[^>]*class="[^"]*table[^"]*"[^>]*>(.*?)</table>',
        page, re.DOTALL | re.IGNORECASE
    )
    if not table_match:
        return []

    table_html = table_match.group(1)
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL | re.IGNORECASE)

    def clean_cell(s):
        s = re.sub(r'<[^>]+>', ' ', s)
        s = html.unescape(s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    records = []
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
        if len(cells) < 2:
            continue

        commission = clean_cell(cells[0])
        date_time  = clean_cell(cells[1]) if len(cells) > 1 else ""
        location   = clean_cell(cells[2]) if len(cells) > 2 else ""
        agenda_raw = cells[3]             if len(cells) > 3 else ""

        if not commission:
            continue

        parts = re.split(r'<hr\s*/?>', agenda_raw, flags=re.IGNORECASE)
        agenda_header = clean_cell(parts[0]) if parts else ""
        agenda_items  = clean_cell(parts[1]) if len(parts) > 1 else ""

        source_summary = agenda_header
        if agenda_items:
            source_summary += (" | " if source_summary else "") + agenda_items

        title = f"{commission} – {date_time}" if date_time else commission

        records.append({
            "institution":    "TBMM",
            "source_type":    "komisyon_gundemleri",
            "title":          title,
            "date_text":      date_time,
            "location":       location,
            "link":           url,
            "source_summary": source_summary.strip(),
        })

    return records

def main():
    # config.json'dan aktif kurumları oku
    enabled = None
    config_file = Path("/root/monitoring/panel/config.json")
    if config_file.exists():
        try:
            cfg = json.loads(config_file.read_text(encoding="utf-8"))
            enabled = set(cfg.get("institutions", {}).get("enabled", []))
        except Exception:
            pass

    def inc(name):
        return enabled is None or name in enabled

    combined = []
    if inc("SPK"):                    combined.extend(parse_spk_today())
    if inc("BDDK"):                   combined.extend(parse_bddk_today())
    if inc("Ticaret Bakanlığı"):      combined.extend(parse_ticaret_today())
    if inc("EPDK"):                   combined.extend(parse_epdk_today())
    if inc("Rekabet Kurumu"):         combined.extend(parse_rekabet_today())
    if inc("İstanbul Ticaret Odası"): combined.extend(parse_ito_today())
    if inc("TBMM"):                   combined.extend(parse_tbmm_genel_kurul_today())
    if inc("TBMM"):                   combined.extend(parse_tbmm_komisyon_today())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(combined)} records to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
