FROM python:3.11-slim

# Sistem paketleri
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

# Google Chrome kurulumu - Stable version
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Chrome versiyonunu kontrol et ve uyumlu ChromeDriver indir
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1-3) \
    && echo "Installed Chrome version: $CHROME_VERSION" \
    && CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d. -f1) \
    && echo "Chrome major version: $CHROME_MAJOR_VERSION" \
    && if [ "$CHROME_MAJOR_VERSION" -ge "115" ]; then \
        echo "Using Chrome for Testing API for version $CHROME_VERSION" \
        && CHROMEDRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_$CHROME_MAJOR_VERSION") \
        && echo "ChromeDriver version to download: $CHROMEDRIVER_VERSION" \
        && wget -q "https://storage.googleapis.com/chrome-for-testing-public/$CHROMEDRIVER_VERSION/linux64/chromedriver-linux64.zip" \
        && unzip chromedriver-linux64.zip \
        && mv chromedriver-linux64/chromedriver /usr/bin/chromedriver \
        && chmod +x /usr/bin/chromedriver \
        && rm -rf chromedriver-linux64.zip chromedriver-linux64; \
    else \
        echo "Using legacy ChromeDriver API" \
        && CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION") \
        && echo "ChromeDriver version: $CHROMEDRIVER_VERSION" \
        && wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" \
        && unzip chromedriver_linux64.zip -d /usr/bin \
        && chmod +x /usr/bin/chromedriver \
        && rm chromedriver_linux64.zip; \
    fi \
    && echo "ChromeDriver installation completed" \
    && chromedriver --version

WORKDIR /app

# Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Gerekli klasörleri oluştur
RUN mkdir -p data logs

# Çevre değişkenleri
ENV IS_RENDER=true
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

EXPOSE 10000

# Startup script
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
