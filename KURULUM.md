# Legal Radar — Kurulum Kılavuzu

Bu sistem her sabah otomatik olarak üç farklı e-posta gönderir:
- 📋 Resmî Gazete özeti
- 🏛 Kurumsal duyuru özeti (resmi kurumların günlük duyuruları)
- 📊 Sektörel haber özeti

Kurulumu tamamladıktan sonra sistemi yönetmek için teknik bilgiye ihtiyacınız olmayacak.
Her şeyi tarayıcınızdan açılan bir panel üzerinden yönetebileceksiniz.

---

## 🔒 Güvenlik ve Gizlilik Hakkında

Bu sistemi kurmadan önce şunları bilmeniz önemlidir:

**Verileriniz yalnızca sizin sunucunuzda saklanır.**
Girdiğiniz mail şifresi, API anahtarı ve alıcı adresleri yalnızca kendi satın aldığınız
sunucuda (VPS) tutulur. Bu bilgiler hiçbir üçüncü tarafla paylaşılmaz, hiçbir bulut
sistemine gönderilmez.

**Mail şifresi olarak normal şifrenizi kullanmayın.**
Gmail özelinde "Uygulama Şifresi" adı verilen ayrı bir şifre oluşturmanız gerekir.
Bu şifre yalnızca bu sistem tarafından kullanılır; hesabınıza tam erişim sağlamaz.
Şifreyi iptal etmek istediğinizde Google hesabınızdan tek tıkla silebilirsiniz.

**Gemini API anahtarı ücretli işlem başlatmaz.**
Ücretsiz kota dahilinde çalışır. Ücretli kullanıma geçmek için ayrıca onay vermeniz gerekir.

**Panele şifre ile giriş yapılır.**
Kurulum sırasında belirlediğiniz şifre olmadan kimse panele erişemez.

---

## Kurulum Özeti

Kurulum 6 ana adımdan oluşur:

1. VPS (sunucu) satın almak
2. Sunucuya bağlanmak
3. Gmail Uygulama Şifresi almak
4. Gemini API anahtarı almak
5. Sistemi kurmak
6. Panelden ayarları girmek

Toplam süre: yaklaşık 45-60 dakika

---

## Adım 1 — VPS Satın Almak

VPS (Virtual Private Server), internetin her yerinden çalışan küçük bir bilgisayardır.
Sisteminizi 7/24 çalıştırabilmek için buna ihtiyacınız var.

### Önerilen Sağlayıcı: Hetzner

Hetzner Avrupa merkezli, güvenilir ve uygun fiyatlı bir sağlayıcıdır.

1. https://www.hetzner.com adresine gidin
2. Sağ üstten "Sign Up" ile hesap oluşturun
3. E-posta doğrulamasını tamamlayın
4. Sol menüden "Cloud" → "Projects" → "New Project" deyin
5. Projeye istediğiniz bir isim verin (örn: "monitoring")
6. "Add Server" butonuna tıklayın
7. Şu seçimleri yapın:
   - **Location:** Nuremberg veya Helsinki (Avrupa)
   - **Image:** Ubuntu 24.04
   - **Type:** Shared vCPU → "CX22" (2 vCPU, 4GB RAM) — aylık ~4-5€
   - **SSH Key:** Şimdilik atlayın, "Root Password" seçin
8. "Create & Buy Now" butonuna tıklayın

Birkaç dakika içinde sunucunuz hazır olacak ve size bir **IP adresi** gösterilecek.
Bu IP adresini bir yere not edin — her adımda kullanacaksınız.

Ayrıca kurulum sırasında size e-posta ile bir **root şifresi** gönderilecek.
Bu şifreyi de not edin.

> 💡 Alternatif sağlayıcılar: DigitalOcean (digitalocean.com),
> Contabo (contabo.com), Hostinger (hostinger.com.tr)

---

## Adım 2 — Sunucuya Bağlanmak

Sunucuya bağlanmak için bilgisayarınızda bir terminal uygulaması kullanacaksınız.

### Windows'ta bağlanma:

1. Başlat menüsünden "CMD" veya "PowerShell" aratın ve açın
2. Şu komutu yazın (IP_ADRESINIZ yerine gerçek IP'yi yazın):
ssh root@IP_ADRESINIZ

3. "Are you sure you want to continue connecting?" sorusuna `yes` yazın
4. Hetzner'den gelen root şifrenizi girin (yazarken ekranda görünmez, bu normal)
5. Sisteme girdiğinizde `root@sunucu:~#` şeklinde bir satır göreceksiniz
İlk girişte şifrenizi değiştirmeniz istenebilir. Güçlü bir şifre belirleyin.
---
## Adım 3 — Gmail Uygulama Şifresi Almak
> ⚠️ Bu adım için Gmail hesabınızda 2 Adımlı Doğrulama açık olmalıdır.
### 2 Adımlı Doğrulamayı açmak için:
1. https://myaccount.google.com adresine gidin
2. Sol menüden "Güvenlik" seçin
3. "Google'da oturum açma" bölümünden "2 Adımlı Doğrulama"ya tıklayın
4. Adımları takip ederek etkinleştirin
### Uygulama Şifresi oluşturmak için:
1. https://myaccount.google.com/apppasswords adresine gidin
2. "Uygulama adı" alanına "Monitoring" yazın
3. "Oluştur" butonuna tıklayın
4. Ekranda 16 haneli bir şifre görünecek (örn: `abcd efgh ijkl mnop`)
5. Bu şifreyi kopyalayın — bir daha gösterilmeyecek
> 🔒 Bu şifre normal Gmail şifrenizden farklıdır ve yalnızca bu sisteme özeldir.
> İstediğiniz zaman aynı sayfadan "Sil" diyerek iptal edebilirsiniz.
---
## Adım 4 — Gemini API Anahtarı Almak
Gemini, Google'ın yapay zeka servisidir. Sisteminiz haberleri ve duyuruları
özetlemek için bunu kullanır.
1. https://aistudio.google.com adresine gidin
2. Google hesabınızla giriş yapın
3. Sol menüden "API Keys" seçin
4. "Create API Key" butonuna tıklayın
5. "Create API key in new project" seçin
6. Oluşturulan anahtarı kopyalayın
> 🆓 Ücretsiz kotayla günde 20 istek hakkınız var. Günlük üç pipeline bu kotanın
> içinde kalır. Ücretli kullanıma geçmek için ayrıca kart bilgisi girip onay vermeniz gerekir.
---
## Adım 5 — Sistemi Kurmak
Sunucu terminalinde (SSH bağlantısı açıkken) aşağıdaki komutları sırasıyla çalıştırın.
Her komuttan sonra Enter'a basın ve tamamlanmasını bekleyin.
### 5.1 — Sistemi güncelleyin
```bash
apt update && apt upgrade -y
Bu işlem 2-5 dakika sürebilir.

5.2 — Gerekli paketleri yükleyin
apt install -y python3 python3-pip python3-venv curl nano
5.3 — Klasör yapısını oluşturun
mkdir -p /root/monitoring/institutions
mkdir -p /root/monitoring/news
mkdir -p /root/monitoring/output
mkdir -p /root/monitoring/panel
5.4 — Dosyaları kopyalayın
Bu kılavuzla birlikte gelen dosyaları sunucunuza aktarmanız gerekir.
Bunun için bilgisayarınızda yeni bir CMD/PowerShell penceresi açın
(SSH bağlantısını kapatmadan) ve şu komutları çalıştırın:

scp -r DOSYA_KLASÖRÜ/phase1/* root@IP_ADRESINIZ:/root/
scp -r DOSYA_KLASÖRÜ/phase2/* root@IP_ADRESINIZ:/root/monitoring/institutions/
scp -r DOSYA_KLASÖRÜ/phase3/* root@IP_ADRESINIZ:/root/monitoring/news/
scp -r DOSYA_KLASÖRÜ/panel/* root@IP_ADRESINIZ:/root/monitoring/panel/
DOSYA_KLASÖRÜ yerine bu dosyaların bulunduğu klasörün tam yolunu yazın.
Örnek: C:\Users\KullaniciAdi\Desktop\legal-radar-export

5.5 — Script izinlerini ayarlayın
SSH terminalinde:

chmod +x /root/run_rg_mail.sh
chmod +x /root/monitoring/institutions/run_institutions_pipeline.sh
chmod +x /root/monitoring/news/run_news_pipeline.sh
5.6 — Python ortamlarını kurun
python3 -m venv /root/monitoring/venv
/root/monitoring/venv/bin/pip install google-genai

python3 -m venv /root/monitoring/news/venv
/root/monitoring/news/venv/bin/pip install feedparser google-genai

python3 -m venv /root/monitoring/panel/venv
/root/monitoring/panel/venv/bin/pip install streamlit
Her kurulum 1-3 dakika sürebilir.

5.7 — Panel servisini oluşturun
Şu komutu tek seferde kopyalayıp terminale yapıştırın:

cat > /etc/systemd/system/legalradar-panel.service << 'EOF'
[Unit]
Description=Legal Radar Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/monitoring/panel
ExecStart=/root/monitoring/panel/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
Ardından servisi başlatın:

systemctl daemon-reload
systemctl enable legalradar-panel
systemctl start legalradar-panel
5.8 — Güvenlik duvarında port açın
ufw allow 22/tcp
ufw allow 8501/tcp
ufw --force enable
Adım 6 — Panelden Ayarları Girmek
Tarayıcınızı açın ve şu adresi yazın:
http://IP_ADRESINIZ:8501
Karşınıza giriş ekranı gelecek. Varsayılan şifre: changeme123
Sol menüden ⚙️ Ayarlar sayfasına gidin ve şu bilgileri doldurun:
Alan	Nereden Alınır
SMTP Sunucu	Gmail için: smtp.gmail.com
Port	587
Gönderici E-posta	Gmail adresiniz
Uygulama Şifresi	Adım 3'te oluşturduğunuz 16 haneli şifre
Gönderici Görünen Adı	Örn: Legal Radar - Legal <adres@sirket.com>
Mail Alıcıları	Virgülle ayırarak istediğiniz adresleri yazın
Gemini API Anahtarı	Adım 4'te kopyaladığınız anahtar
Panel Şifresi	changeme123 yerine kendi şifrenizi belirleyin
"💾 Kaydet" butonuna tıklayın.
Sol menüden ⏰ Zamanlama sayfasına gidin:
Resmî Gazete: Saat 9, Dakika 5 (önerilir)
Kurumsal Duyurular: Saat 9, Dakika 0 (önerilir)
Sektörel Haberler: Saat 9, Dakika 10 (önerilir)
"💾 Güncelle" butonuna tıklayın.
Sol menüden 🎨 Özelleştirme sayfasına gidin:
İhtiyacınıza göre sektörleri ve anahtar kelimeleri düzenleyin
Takip etmek istediğiniz kurumları işaretleyin
Sol menüden 🧪 Manuel Test sayfasına gidin ve
"▶ Şimdi Çalıştır" butonlarına tıklayarak sistemin çalıştığını doğrulayın.
Kurulum Tamamlandı
Her şey doğru kurulduysa:

Her sabah belirlediğiniz saatte otomatik mailler gelecek
Panel her zaman http://IP_ADRESINIZ:8501 adresinden erişilebilir olacak
Sunucu yeniden başlasa bile panel otomatik olarak açılacak
Sık Sorulan Sorular
Mail gelmiyor, ne yapmalıyım?
Panel → 🧪 Manuel Test → ilgili pipeline için "Şimdi Çalıştır" butonuna tıklayın.
Çıktıda hata mesajı varsa SMTP bilgilerinizi kontrol edin.

Uygulama şifremi kaybettim.
https://myaccount.google.com/apppasswords adresinden yenisini oluşturun,
Panel → ⚙️ Ayarlar'dan güncelleyin.

Yeni sektör eklemek istiyorum.
Panel → 🎨 Özelleştirme → Sektörler bölümünden "➕ Yeni Sektör Ekle" ile ekleyebilirsiniz.

Hangi kurumlar destekleniyor?
Sistem birden fazla Türk düzenleyici kurumunu takip eder.
Panelin Özelleştirme sayfasından hangi kurumların aktif olduğunu görebilir ve değiştirebilirsiniz.

Aylık maliyeti nedir?
Yalnızca VPS maliyeti — Hetzner CX22 için yaklaşık 4-5€/ay.
Gemini API ücretsiz kotayla çalışır.
