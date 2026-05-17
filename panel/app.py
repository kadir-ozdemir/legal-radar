#!/usr/bin/env python3
# Legal Radar Panel

import streamlit as st
import subprocess
import json

from pathlib import Path
from datetime import datetime

ENV_FILE   = Path("/root/monitoring/.mail_env")
CONFIG_FILE = Path("/root/monitoring/panel/config.json")

ALL_INSTITUTIONS = [
    "SPK", "BDDK", "EPDK", "Rekabet Kurumu",
    "Ticaret Bakanlığı", "İstanbul Ticaret Odası", "TBMM"
]

def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"news": {"sectors": {}, "rss_feeds": {}}, "institutions": {"enabled": ALL_INSTITUTIONS[:]}}

def save_config(config):
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
LOG_RG     = Path("/root/rg_mail.log")
LOG_INST   = Path("/root/monitoring/output/institutions_cron.log")
LOG_NEWS   = Path("/root/monitoring/news/news_cron.log")


def load_env():
    env = {}
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"')
    return env


def save_env(env):
    lines = []
    for k, v in env.items():
        if any(c in v for c in [" ", "<", ">", ","]):
            lines.append(f'{k}="{v}"')
        else:
            lines.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_crontab():
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def set_crontab(content):
    subprocess.run(["crontab", "-"], input=content, text=True, check=True)


def parse_cron_time(crontab, keyword):
    for line in crontab.splitlines():
        if keyword in line and not line.strip().startswith("#"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    return int(parts[0]), int(parts[1])
                except ValueError:
                    pass
    return None, None


def update_cron_time(crontab, keyword, minute, hour):
    lines = []
    for line in crontab.splitlines():
        if keyword in line and not line.strip().startswith("#"):
            parts = line.split()
            if len(parts) >= 6:
                parts[0] = str(minute)
                parts[1] = str(hour)
                line = " ".join(parts)
        lines.append(line)
    return "\n".join(lines) + "\n"


def tail_log(path, n=40):
    if not path.exists():
        return "Log henüz oluşturulmamış."
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:]) if lines else "Log boş."


def run_script(script):
    cmd = f'bash -c "set -a; source {ENV_FILE}; set +a; bash {script} 2>&1"'
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        return (r.stdout + r.stderr).strip() or "(çıktı yok)"
    except subprocess.TimeoutExpired:
        return "Zaman aşımı (180s)"
    except Exception as e:
        return f"Hata: {e}"


def check_auth():
    if st.session_state.get("auth"):
        return True
    env = load_env()
    pw_correct = env.get("PANEL_PASSWORD", "changeme123")
    st.title("⚖️ Legal Radar")
    st.markdown("---")
    with st.form("login_form"):
        pw = st.text_input("Şifre", type="password", placeholder="Panel şifrenizi girin")
        if st.form_submit_button("Giriş Yap", use_container_width=True, type="primary"):
            if pw == pw_correct:
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Yanlış şifre.")
    return False


def page_dashboard():
    st.title("🏠 Ana Sayfa")
    st.caption(f"Sunucu saati: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    crontab = get_crontab()
    c1, c2, c3 = st.columns(3)
    for col, kw, label in [
        (c1, "run_rg_mail",      "📋 Resmî Gazete"),
        (c2, "run_institutions", "🏛 Kurumsal Duyurular"),
        (c3, "run_news",         "📊 Sektörel Haberler"),
    ]:
        m, h = parse_cron_time(crontab, kw)
        with col:
            st.metric(label, f"✅ {h:02d}:{m:02d}" if m is not None else "❌ Pasif")
    st.divider()
    st.subheader("📄 Son Loglar")
    t1, t2, t3 = st.tabs(["📋 Resmî Gazete", "🏛 Kurumsal", "📊 Haberler"])
    with t1:
        st.code(tail_log(LOG_RG))
    with t2:
        st.code(tail_log(LOG_INST))
    with t3:
        st.code(tail_log(LOG_NEWS))


def page_settings():
    st.title("⚙️ Ayarlar")
    env = load_env()
    with st.form("settings_form"):
        st.subheader("📧 SMTP Ayarları")
        c1, c2 = st.columns(2)
        with c1:
            smtp_host = st.text_input("SMTP Sunucu", value=env.get("RG_SMTP_HOST", "smtp.gmail.com"))
            smtp_user = st.text_input("Gönderici E-posta", value=env.get("RG_SMTP_USER", ""))
        with c2:
            smtp_port = st.text_input("Port", value=env.get("RG_SMTP_PORT", "587"))
            smtp_pass = st.text_input("Uygulama Şifresi", value=env.get("RG_SMTP_APP_PASSWORD", ""), type="password")
        mail_from = st.text_input(
            "Gönderici Görünen Adı",
            value=env.get("RG_MAIL_FROM", ""),
            placeholder="Legal Radar - Legal <gonderici@sirket.com>"
        )
        st.divider()
        st.subheader("👥 Alıcılar")
        mail_to  = st.text_area("Mail Alıcıları (virgülle ayırın)",
                                 value=env.get("INSTITUTIONS_MAIL_TO", ""), height=80)
        error_to = st.text_input("Hata Bildirimi Alıcısı",
                                  value=env.get("INSTITUTIONS_ERROR_MAIL_TO", ""))
        st.divider()
        st.subheader("🤖 Gemini API")
        gemini_key = st.text_input("API Anahtarı", value=env.get("GEMINI_API_KEY", ""), type="password")
        opts = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        cur  = env.get("GEMINI_MODEL", "gemini-2.5-flash")
        gemini_model = st.selectbox("Model", opts, index=opts.index(cur) if cur in opts else 0)
        st.divider()
        st.subheader("🔐 Panel Güvenliği")
        panel_pw = st.text_input("Panel Şifresi",
                                  value=env.get("PANEL_PASSWORD", "changeme123"), type="password")
        if st.form_submit_button("💾 Kaydet", type="primary", use_container_width=True):
            save_env({
                "RG_SMTP_HOST":               smtp_host.strip(),
                "RG_SMTP_PORT":               smtp_port.strip(),
                "RG_SMTP_USER":               smtp_user.strip(),
                "RG_SMTP_APP_PASSWORD":       smtp_pass.strip(),
                "RG_MAIL_FROM":               mail_from.strip(),
                "INSTITUTIONS_MAIL_TO":       mail_to.replace("\n", "").strip(),
                "INSTITUTIONS_ERROR_MAIL_TO": error_to.strip(),
                "GEMINI_API_KEY":             gemini_key.strip(),
                "GEMINI_MODEL":               gemini_model,
                "PANEL_PASSWORD":             panel_pw.strip(),
            })
            st.success("✅ Ayarlar kaydedildi!")


def page_schedule():
    st.title("⏰ Zamanlama")
    st.caption("Her pipeline için günlük çalışma saatini ayarlayın.")
    crontab = get_crontab()
    rg_m,   rg_h   = parse_cron_time(crontab, "run_rg_mail")
    inst_m, inst_h = parse_cron_time(crontab, "run_institutions")
    news_m, news_h = parse_cron_time(crontab, "run_news")
    with st.form("schedule_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("📋 Resmî Gazete")
            rg_hour = st.number_input("Saat",   0, 23, rg_h   or 9, key="rgh")
            rg_min  = st.number_input("Dakika", 0, 59, rg_m   or 5, key="rgm")
        with c2:
            st.subheader("🏛 Kurumsal")
            ih = st.number_input("Saat",   0, 23, inst_h or 9, key="ih")
            im = st.number_input("Dakika", 0, 59, inst_m or 0, key="im")
        with c3:
            st.subheader("📊 Haberler")
            nh = st.number_input("Saat",   0, 23, news_h or 9,  key="nh")
            nm = st.number_input("Dakika", 0, 59, news_m or 10, key="nm")
        if st.form_submit_button("💾 Güncelle", type="primary", use_container_width=True):
            ct = update_cron_time(crontab, "run_rg_mail",     rg_min, rg_hour)
            ct = update_cron_time(ct,      "run_institutions", im,     ih)
            ct = update_cron_time(ct,      "run_news",         nm,     nh)
            set_crontab(ct)
            st.success("✅ Zamanlama güncellendi!")
            st.rerun()


def page_test():
    st.title("🧪 Manuel Test")
    st.info("Butonlar pipeline'ı anında çalıştırır ve gerçek mail gönderir.", icon="ℹ️")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("📋 Resmî Gazete")
        if st.button("▶ Şimdi Çalıştır", key="rg", use_container_width=True):
            with st.spinner("Çalışıyor..."):
                st.code(run_script("/root/run_rg_mail.sh"))
    with c2:
        st.subheader("🏛 Kurumsal")
        if st.button("▶ Şimdi Çalıştır", key="inst", use_container_width=True):
            with st.spinner("Çalışıyor... (~2-3 dk)"):
                st.code(run_script("/root/monitoring/institutions/run_institutions_pipeline.sh"))
    with c3:
        st.subheader("📊 Haberler")
        if st.button("▶ Şimdi Çalıştır", key="news", use_container_width=True):
            with st.spinner("Çalışıyor..."):
                st.code(run_script("/root/monitoring/news/run_news_pipeline.sh"))


def page_customize():
    st.title("🎨 Özelleştirme")
    config = load_config()

    tab1, tab2 = st.tabs(["📊 Sektörler & Haber Kaynakları", "🏛 Takip Edilen Kurumlar"])

    with tab1:
        # ── RSS Kaynakları ────────────────────────────────────────────
        st.subheader("📰 Haber Kaynakları (RSS)")
        rss_feeds = config.get("news", {}).get("rss_feeds", {})

        for name, url in list(rss_feeds.items()):
            c1, c2, c3 = st.columns([3, 6, 1])
            c1.write(f"**{name}**")
            c2.caption(url)
            if c3.button("🗑", key=f"del_rss_{name}"):
                del rss_feeds[name]
                config["news"]["rss_feeds"] = rss_feeds
                save_config(config)
                st.rerun()

        with st.expander("➕ Yeni Kaynak Ekle"):
            with st.form("add_rss_form"):
                new_name = st.text_input("Kaynak Adı", placeholder="Örn: Hürriyet Ekonomi")
                new_url  = st.text_input("RSS URL", placeholder="https://www.hurriyet.com.tr/rss/ekonomi")
                if st.form_submit_button("Ekle", type="primary"):
                    if new_name.strip() and new_url.strip():
                        rss_feeds[new_name.strip()] = new_url.strip()
                        config["news"]["rss_feeds"] = rss_feeds
                        save_config(config)
                        st.success(f"✅ {new_name} eklendi!")
                        st.rerun()

        st.divider()

        # ── Sektörler ─────────────────────────────────────────────────
        st.subheader("🏷️ Sektörler ve Anahtar Kelimeler")
        st.caption("Her sektörde bu kelimelerden biri geçen haberler mail'e dahil edilir.")
        sectors = config.get("news", {}).get("sectors", {})

        sector_to_delete = None
        for sector_name, sector_data in sectors.items():
            with st.expander(f"🏷️ {sector_name}"):
                kws = ", ".join(sector_data.get("keywords", []))
                new_kws = st.text_area("Anahtar kelimeler (virgülle ayırın)",
                                        value=kws, key=f"kw_{sector_name}", height=80)
                c1, c2 = st.columns([5, 1])
                with c1:
                    if st.button("💾 Kaydet", key=f"save_s_{sector_name}"):
                        kw_list = [k.strip() for k in new_kws.split(",") if k.strip()]
                        sectors[sector_name]["keywords"] = kw_list
                        config["news"]["sectors"] = sectors
                        save_config(config)
                        st.success("✅ Güncellendi!")
                with c2:
                    if st.button("🗑 Sil", key=f"del_s_{sector_name}"):
                        sector_to_delete = sector_name

        if sector_to_delete:
            del sectors[sector_to_delete]
            config["news"]["sectors"] = sectors
            save_config(config)
            st.rerun()

        with st.expander("➕ Yeni Sektör Ekle"):
            with st.form("add_sector_form"):
                new_sector  = st.text_input("Sektör Adı", placeholder="Örn: Sağlık")
                new_color   = st.color_picker("Renk", "#3498db")
                new_kws_str = st.text_area("Anahtar Kelimeler (virgülle ayırın)", height=80,
                                            placeholder="sağlık, hastane, ilaç, eczane, klinik")
                if st.form_submit_button("Sektör Ekle", type="primary"):
                    if new_sector.strip() and new_kws_str.strip():
                        kw_list = [k.strip() for k in new_kws_str.split(",") if k.strip()]
                        sectors[new_sector.strip()] = {"keywords": kw_list, "color": new_color}
                        config["news"]["sectors"] = sectors
                        save_config(config)
                        st.success(f"✅ {new_sector} eklendi!")
                        st.rerun()

    with tab2:
        st.subheader("🏛 Takip Edilen Kurumlar")
        st.caption("İşaretli kurumlar günlük duyuru özetine dahil edilir.")
        enabled = config.get("institutions", {}).get("enabled", ALL_INSTITUTIONS[:])

        new_enabled = []
        cols = st.columns(3)
        for i, inst in enumerate(ALL_INSTITUTIONS):
            with cols[i % 3]:
                if st.checkbox(inst, value=(inst in enabled), key=f"inst_{inst}"):
                    new_enabled.append(inst)

        st.write("")
        if st.button("💾 Kaydet", type="primary"):
            config["institutions"] = {"enabled": new_enabled}
            save_config(config)
            st.success("✅ Kurum ayarları güncellendi!")

def render_footer():
    st.markdown(
        "<div style='text-align:center; color:#888; font-size:0.8em; padding-top:2em;'>"
        "Built by Kadir Özdemir"
        "</div>",
        unsafe_allow_html=True,
    )

def main():
    st.set_page_config(page_title="Legal Radar", page_icon="⚖️", layout="wide")
    if not check_auth():
        return
    pages = {
        "🏠 Ana Sayfa":   page_dashboard,
        "⚙️ Ayarlar":     page_settings,
        "⏰ Zamanlama":   page_schedule,
        "🎨 Özelleştirme":  page_customize,
        "🧪 Manuel Test": page_test,
    }
    with st.sidebar:
        st.title("⚖️ Legal Radar")
        st.caption("Hukuki Bilgi Takip Sistemi")
        st.divider()
        choice = st.radio("", list(pages.keys()), label_visibility="collapsed")
        st.divider()
        if st.button("🚪 Çıkış", use_container_width=True):
            st.session_state["auth"] = False
            st.rerun()
        st.caption("v1.0 · Legal Radar")
    pages[choice]()
    render_footer()


if __name__ == "__main__":
    main()
