# Web3 Twitter Bot

Bu bot, Web3 projeleri hakkında otomatik içerik paylaşımı yapan ve belirli Twitter hesaplarının tweetlerine yanıt veren gelişmiş bir Python uygulamasıdır.

## Özellikler

- ✅ Twitter'a otomatik giriş ve session yönetimi
- ✅ Saatlik otomatik içerik paylaşımı (Web3 projeleri)
- ✅ Gemini AI ile içerik üretimi
- ✅ Belirli hesapları takip etme ve tweetlerine yanıt verme
- ✅ Render.com uyumlu yapılandırma

## Kurulum

### 1. Gereksinimler

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 2. Konfigürasyon

`.env` dosyasını oluşturun ve aşağıdaki bilgileri ekleyin:

\`\`\`
GEMINI_API_KEY=your_gemini_api_key
EMAIL_USER=your_email@example.com
EMAIL_PASS=your_email_password
TWITTER_USERNAME=your_twitter_username
TWITTER_PASSWORD=your_twitter_password
\`\`\`

### 3. Çalıştırma

\`\`\`bash
python main.py
\`\`\`

### Render.com ile Çalıştırma

1. Render.com hesabınıza giriş yapın
2. "New +" butonuna tıklayın ve "Web Service" seçin
3. GitHub reponuzu bağlayın
4. Environment Variables bölümünde gerekli değişkenleri ekleyin
5. "Create Web Service" butonuna tıklayın

## Çalışma Mantığı

- Her saat başı 2 Web3 projesi seçilir ve içerik üretilip paylaşılır
- Her saat 30. dakikada takip edilen hesapların son tweetleri kontrol edilir
- Son 1 saat içinde atılmış tweetlere yanıt verilir
- Tüm aktiviteler loglanır

## Güvenlik

- API anahtarlarınızı ve giriş bilgilerinizi güvenli tutun
- Rate limit'lere dikkat edin
- Bot aktivitelerini düzenli kontrol edin
