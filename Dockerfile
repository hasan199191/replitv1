FROM python:3.11-slim

# Render.com için gerekli sistem paketleri
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Belirli bir Chrome sürümünü yükle
RUN wget -q -O chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_119.0.6045.159-1_amd64.deb \
    && apt-get update \
    && apt-get install -y ./chrome.deb \
    && rm chrome.deb \
    && rm -rf /var/lib/apt/lists/*

# Uygun ChromeDriver sürümünü yükle
RUN wget -q "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/119.0.6045.159/linux64/chromedriver-linux64.zip" \
    && unzip chromedriver-linux64.zip \
    && mv chromedriver-linux64/chromedriver /usr/bin/chromedriver \
    && chmod +x /usr/bin/chromedriver \
    && rm -rf chromedriver-linux64.zip chromedriver-linux64

# Çalışma dizini
WORKDIR /app

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Data ve logs klasörlerini oluştur
RUN mkdir -p data logs

# Render.com için çevre değişkenleri
ENV IS_RENDER=true
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Port (Render için gerekli olabilir)
EXPOSE 10000

# Health check endpoint için basit HTTP server
COPY health_server.py .

# Startup script
COPY start.sh .
RUN chmod +x start.sh

# Uygulamayı çalıştır
CMD ["./start.sh"]
