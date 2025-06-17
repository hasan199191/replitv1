FROM python:3.11-slim

# Sistem paketleri
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ca-certificates \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Playwright browsers yükle (sadece Chromium)
RUN playwright install chromium
RUN playwright install-deps chromium

# Uygulama dosyalarını kopyala
COPY . .

# Gerekli klasörleri oluştur
RUN mkdir -p data logs /tmp/playwright_data

# Çevre değişkenleri
ENV IS_RENDER=true
ENV PYTHONUNBUFFERED=1

EXPOSE 10000

# Startup script
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
