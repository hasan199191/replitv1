import os
import time
import random
import logging
import smtplib
import ssl
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException, JavascriptException
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import subprocess

class TwitterBrowser:
    def __init__(self, headless=True, debug=False):
        self.headless = headless
        self.debug = debug
        self.logger = self.setup_logger()
        self.driver = None
        self.wait_time = 10
        self.short_wait_time = 5
        self.scroll_pause_time = 2
        self.max_attempts = 3
        self.email_sender = os.environ.get('EMAIL_USER')
        self.email_password = os.environ.get('EMAIL_PASS')
        self.email_receiver = os.environ.get('EMAIL_RECEIVER')
        self.twitter_username = os.environ.get('TWITTER_USERNAME')
        self.twitter_password = os.environ.get('TWITTER_PASSWORD')
        self.is_initialized = False

    def setup_logger(self):
        """Logger'ı ayarlar."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        
        # Aynı logger'a birden fazla handler eklenmesini önle
        if not logger.hasHandlers():
            ch = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)
        
        return logger

    def get_chrome_version(self):
        """Chrome versiyonunu tespit eder."""
        try:
            output = subprocess.check_output(['google-chrome', '--version'])
            version = output.decode('utf-8').strip()
            return version
        except FileNotFoundError:
            self.logger.warning("Google Chrome bulunamadı.")
            return None
        except Exception as e:
            self.logger.error(f"Chrome versiyonu alınırken hata oluştu: {e}")
            return None

    def initialize(self):
        """Tarayıcıyı başlat"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--mute-audio")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
            
            # Render.com için özel ayarlar
            if os.environ.get('IS_RENDER'):
                chrome_options.add_argument("--disable-background-timer-throttling")
                chrome_options.add_argument("--disable-backgrounding-occluded-windows")
                chrome_options.add_argument("--disable-renderer-backgrounding")
                chrome_options.add_argument("--disable-features=TranslateUI")
                chrome_options.add_argument("--disable-ipc-flooding-protection")
                chrome_options.binary_location = "/usr/bin/google-chrome"
            
            # Chrome versiyonunu kontrol et
            chrome_version = self.get_chrome_version()
            
            # ChromeDriver service oluştur
            service = None
            
            # 1. Önce sistem ChromeDriver'ını dene
            if os.path.exists('/usr/bin/chromedriver'):
                try:
                    service = Service('/usr/bin/chromedriver')
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    self.logger.info("Successfully using system ChromeDriver")
                    
                    # Debug: Environment variables kontrolü
                    self.logger.info(f"EMAIL_USER set: {'Yes' if os.environ.get('EMAIL_USER') else 'No'}")
                    self.logger.info(f"TWITTER_USERNAME set: {'Yes' if os.environ.get('TWITTER_USERNAME') else 'No'}")
                    self.logger.info(f"TWITTER_PASSWORD set: {'Yes' if os.environ.get('TWITTER_PASSWORD') else 'No'}")
                    
                    return True
                except Exception as e:
                    self.logger.warning(f"System ChromeDriver failed: {e}")
            
            # 2. Eğer sistemde yoksa, webdriver_manager ile kurmayı dene
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.logger.info("Successfully using webdriver_manager ChromeDriver")
                
                # Debug: Environment variables kontrolü
                self.logger.info(f"EMAIL_USER set: {'Yes' if os.environ.get('EMAIL_USER') else 'No'}")
                self.logger.info(f"TWITTER_USERNAME set: {'Yes' if os.environ.get('TWITTER_USERNAME') else 'No'}")
                self.logger.info(f"TWITTER_PASSWORD set: {'Yes' if os.environ.get('TWITTER_PASSWORD') else 'No'}")
                
                return True
            except Exception as e:
                self.logger.error(f"webdriver_manager ChromeDriver kurulumunda hata: {e}")
                self.send_email(subject="ChromeDriver Hatası", body=f"webdriver_manager ile ChromeDriver kurulurken bir hata oluştu: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Tarayıcı başlatılırken bir hata oluştu: {e}")
            self.send_email(subject="Tarayıcı Başlatma Hatası", body=f"Tarayıcı başlatılırken bir hata oluştu: {e}")
            return False
        finally:
            if self.driver:
                self.is_initialized = True
            else:
                self.is_initialized = False

    def close(self):
        """Tarayıcıyı kapatır."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Tarayıcı başarıyla kapatıldı.")
            except Exception as e:
                self.logger.error(f"Tarayıcı kapatılırken bir hata oluştu: {e}")
        else:
            self.logger.warning("Kapatılacak bir tarayıcı örneği bulunamadı.")

    def navigate(self, url):
        """Belirtilen URL'ye gider."""
        if not self.is_initialized:
            self.logger.error("Tarayıcı başlatılmamış. Lütfen önce initialize() fonksiyonunu çağırın.")
            return False
        try:
            self.driver.get(url)
            self.logger.info(f"Navigated to {url}")
            return True
        except Exception as e:
            self.logger.error(f"URL'ye giderken bir hata oluştu: {e}")
            self.send_email(subject="Navigasyon Hatası", body=f"{url} adresine giderken bir hata oluştu: {e}")
            return False

    def login(self):
        """Twitter'a giriş yapar."""
        if not self.is_initialized:
            self.logger.error("Tarayıcı başlatılmamış. Lütfen önce initialize() fonksiyonunu çağırın.")
            return False

        if not self.twitter_username or not self.twitter_password:
            self.logger.error("Twitter kullanıcı adı veya şifresi tanımlanmamış.")
            self.send_email(subject="Giriş Hatası", body="Twitter kullanıcı adı veya şifresi tanımlanmamış.")
            return False

        try:
            # Giriş sayfasına git
            self.navigate("https://twitter.com/i/flow/login")

            # Kullanıcı adı alanını bul ve kullanıcı adını gir
            username_input = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            username_input.send_keys(self.twitter_username)

            # İleri butonunu bul ve tıkla
            next_button = WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @data-testid='ocfEnterTextNextButton']"))
            )
            next_button.click()

            # Şifre alanını bul ve şifreyi gir
            password_input = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_input.send_keys(self.twitter_password)

            # Giriş yap butonunu bul ve tıkla
            login_button = WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @data-testid='LoginForm_Login_Button']"))
            )
            login_button.click()

            self.logger.info("Twitter'a başarıyla giriş yapıldı.")
            return True

        except TimeoutException:
            self.logger.error("Giriş işlemi sırasında zaman aşımı hatası oluştu.")
            self.send_email(subject="Giriş Hatası", body="Giriş işlemi sırasında zaman aşımı hatası oluştu.")
            return False
        except Exception as e:
            self.logger.error(f"Giriş yapılırken bir hata oluştu: {e}")
            self.send_email(subject="Giriş Hatası", body=f"Giriş yapılırken bir hata oluştu: {e}")
            return False

    def search_and_get_user_info(self, search_query, max_scrolls=5):
        """Arama yapar ve kullanıcı bilgilerini alır."""
        if not self.is_initialized:
            self.logger.error("Tarayıcı başlatılmamış. Lütfen önce initialize() fonksiyonunu çağırın.")
            return []

        try:
            # Arama sayfasına git
            search_url = f"https://twitter.com/search?q={search_query}&src=typed_query"
            if not self.navigate(search_url):
                return []

            user_data = []
            scrolls = 0
            last_height = self.driver.execute_script("return document.body.scrollHeight")

            while scrolls < max_scrolls:
                # Kullanıcıları bul
                users = self.driver.find_elements(By.XPATH, "//div[@data-testid='UserCell']")
                for user in users:
                    try:
                        # Kullanıcı adını al
                        username_element = user.find_element(By.XPATH, ".//a[starts-with(@href, '/')]")
                        username = username_element.get_attribute("href").split('/')[-1]

                        # Adı al
                        name_element = user.find_element(By.XPATH, ".//div[@dir='auto'][1]")
                        name = name_element.text

                        user_data.append({"username": username, "name": name})
                    except NoSuchElementException:
                        self.logger.warning("Kullanıcı bilgisi alınırken bir eleman bulunamadı.")
                        continue

                # Sayfayı aşağı kaydır
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(self.scroll_pause_time)

                # Yeni yüksekliği hesapla ve kaydırma işleminin bitip bitmediğini kontrol et
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scrolls += 1

            self.logger.info(f"{search_query} araması için {len(user_data)} kullanıcı bulundu.")
            return user_data

        except Exception as e:
            self.logger.error(f"Arama yapılırken veya kullanıcı bilgileri alınırken bir hata oluştu: {e}")
            self.send_email(subject="Arama Hatası", body=f"Arama yapılırken veya kullanıcı bilgileri alınırken bir hata oluştu: {e}")
            return []

    def get_user_tweets(self, username, max_tweets=10):
        """Belirli bir kullanıcının tweet'lerini alır."""
        if not self.is_initialized:
            self.logger.error("Tarayıcı başlatılmamış. Lütfen önce initialize() fonksiyonunu çağırın.")
            return []

        try:
            # Kullanıcı profiline git
            profile_url = f"https://twitter.com/{username}"
            if not self.navigate(profile_url):
                return []

            tweets = []
            tweet_count = 0
            last_height = self.driver.execute_script("return document.body.scrollHeight")

            while tweet_count < max_tweets:
                # Tweet'leri bul
                tweet_elements = self.driver.find_elements(By.XPATH, "//div[@data-testid='tweetText']")
                for tweet_element in tweet_elements:
                    try:
                        tweet_text = tweet_element.text
                        tweets.append(tweet_text)
                        tweet_count += 1
                        if tweet_count >= max_tweets:
                            break
                    except StaleElementReferenceException:
                        self.logger.warning("Stale element reference hatası, tweet atlanıyor.")
                        continue

                if tweet_count >= max_tweets:
                    break

                # Sayfayı aşağı kaydır
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(self.scroll_pause_time)

                # Yeni yüksekliği hesapla ve kaydırma işleminin bitip bitmediğini kontrol et
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            self.logger.info(f"{username} kullanıcısından {len(tweets)} tweet alındı.")
            return tweets

        except Exception as e:
            self.logger.error(f"Tweet'ler alınırken bir hata oluştu: {e}")
            self.send_email(subject="Tweet Alma Hatası", body=f"Tweet'ler alınırken bir hata oluştu: {e}")
            return []

    def like_tweet(self, tweet_url):
        """Belirtilen tweet'i beğenir."""
        if not self.is_initialized:
            self.logger.error("Tarayıcı başlatılmamış. Lütfen önce initialize() fonksiyonunu çağırın.")
            return False

        try:
            if not self.navigate(tweet_url):
                return False

            # Beğenme butonunu bul ve tıkla
            like_button = WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@data-testid='like']"))
            )
            like_button.click()

            self.logger.info(f"{tweet_url} beğenildi.")
            return True

        except TimeoutException:
            self.logger.error("Beğenme işlemi sırasında zaman aşımı hatası oluştu.")
            self.send_email(subject="Beğenme Hatası", body="Beğenme işlemi sırasında zaman aşımı hatası oluştu.")
            return False
        except ElementClickInterceptedException as e:
             self.logger.error(f"ElementClickInterceptedException: {e}. Reklam veya başka bir öğe tıklamayı engelliyor olabilir.")
             return False
        except Exception as e:
            self.logger.error(f"Tweet beğenilirken bir hata oluştu: {e}")
            self.send_email(subject="Beğenme Hatası", body=f"Tweet beğenilirken bir hata oluştu: {e}")
            return False

    def retweet(self, tweet_url):
        """Belirtilen tweet'i retweet yapar."""
        if not self.is_initialized:
            self.logger.error("Tarayıcı başlatılmamış. Lütfen önce initialize() fonksiyonunu çağırın.")
            return False

        try:
            if not self.navigate(tweet_url):
                return False

            # Retweet butonunu bul ve tıkla
            retweet_button = WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@data-testid='retweet']"))
            )
            retweet_button.click()

            # Retweet'i onayla (gerekirse)
            confirm_retweet_button = WebDriverWait(self.driver, self.short_wait_time).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@data-testid='retweetConfirm']"))
            )
            confirm_retweet_button.click()

            self.logger.info(f"{tweet_url} retweet yapıldı.")
            return True

        except TimeoutException:
            self.logger.error("Retweet işlemi sırasında zaman aşımı hatası oluştu.")
            self.send_email(subject="Retweet Hatası", body="Retweet işlemi sırasında zaman aşımı hatası oluştu.")
            return False
        except ElementClickInterceptedException as e:
             self.logger.error(f"ElementClickInterceptedException: {e}. Reklam veya başka bir öğe tıklamayı engelliyor olabilir.")
             return False
        except Exception as e:
            self.logger.error(f"Tweet retweet yapılırken bir hata oluştu: {e}")
            self.send_email(subject="Retweet Hatası", body=f"Tweet retweet yapılırken bir hata oluştu: {e}")
            return False

    def follow_user(self, username):
        """Belirtilen kullanıcıyı takip eder."""
        if not self.is_initialized:
            self.logger.error("Tarayıcı başlatılmamış. Lütfen önce initialize() fonksiyonunu çağırın.")
            return False

        try:
            # Kullanıcı profiline git
            profile_url = f"https://twitter.com/{username}"
            if not self.navigate(profile_url):
                return False

            # Takip et butonunu bul ve tıkla
            follow_button = WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@data-testid='placementTracking']//div[@role='button'][span/span/div/text()='Takip Et' or span/div/text()='Follow']"))
            )
            follow_button.click()

            self.logger.info(f"{username} takip edildi.")
            return True

        except TimeoutException:
            self.logger.error("Takip etme işlemi sırasında zaman aşımı hatası oluştu.")
            self.send_email(subject="Takip Etme Hatası", body="Takip etme işlemi sırasında zaman aşımı hatası oluştu.")
            return False
        except ElementClickInterceptedException as e:
             self.logger.error(f"ElementClickInterceptedException: {e}. Reklam veya başka bir öğe tıklamayı engelliyor olabilir.")
             return False
        except Exception as e:
            self.logger.error(f"Kullanıcı takip edilirken bir hata oluştu: {e}")
            self.send_email(subject="Takip Etme Hatası", body=f"Kullanıcı takip edilirken bir hata oluştu: {e}")
            return False

    def send_tweet(self, message):
        """Yeni bir tweet gönderir."""
        if not self.is_initialized:
            self.logger.error("Tarayıcı başlatılmamış. Lütfen önce initialize() fonksiyonunu çağırın.")
            return False

        try:
            # Tweet oluşturma butonunu bul ve tıkla
            tweet_button = WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Tweet'][@role='link']"))
            )
            tweet_button.click()

            # Tweet metin alanını bul ve mesajı gir
            tweet_text_area = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='textbox'][@aria-label='Tweet text']"))
            )
            tweet_text_area.send_keys(message)

            # Tweet gönderme butonunu bul ve tıkla
            send_tweet_button = WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@data-testid='tweetButtonInline']"))
            )
            send_tweet_button.click()

            self.logger.info("Tweet gönderildi.")
            return True

        except TimeoutException:
            self.logger.error("Tweet gönderme işlemi sırasında zaman aşımı hatası oluştu.")
            self.send_email(subject="Tweet Gönderme Hatası", body="Tweet gönderme işlemi sırasında zaman aşımı hatası oluştu.")
            return False
        except Exception as e:
            self.logger.error(f"Tweet gönderilirken bir hata oluştu: {e}")
            self.send_email(subject="Tweet Gönderme Hatası", body=f"Tweet gönderilirken bir hata oluştu: {e}")
            return False

    def send_email(self, subject, body):
        """E-posta gönderir."""
        if not self.email_sender or not self.email_password or not self.email_receiver:
            self.logger.error("E-posta gönderme bilgileri eksik.")
            return False

        try:
            message = MIMEMultipart()
            message['From'] = self.email_sender
            message['To'] = self.email_receiver
            message['Subject'] = subject

            message.attach(MIMEText(body, 'plain'))

            context = ssl.create_default_context()
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
                server.login(self.email_sender, self.email_password)
                server.sendmail(self.email_sender, self.email_receiver, message.as_string())

            self.logger.info("E-posta gönderildi.")
            return True

        except Exception as e:
            self.logger.error(f"E-posta gönderilirken bir hata oluştu: {e}")
            return False
