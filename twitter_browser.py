from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
import pickle
import logging
import random

class TwitterBrowser:
    def __init__(self):
        self.driver = None
        self.cookies_file = 'data/twitter_cookies.pkl'
        self.is_logged_in = False
        self.setup_logging()
        
    def setup_logging(self):
        """Loglama ayarlarını yapılandır"""
        self.logger = logging.getLogger('TwitterBrowser')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
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
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
            
            # Render.com için özel ayarlar
            if os.environ.get('IS_RENDER'):
                chrome_options.binary_location = "/usr/bin/google-chrome"
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.logger.info("Tarayıcı başlatıldı")
            return True
        except Exception as e:
            self.logger.error(f"Tarayıcı başlatılırken hata: {e}")
            return False
    
    def login(self):
        """Twitter'a giriş yap"""
        if not self.driver:
            self.initialize()
        
        try:
            # Önce çerezleri kontrol et
            if self.load_cookies():
                self.logger.info("Çerezler yüklendi, oturum kontrolü yapılıyor")
                self.driver.get("https://twitter.com/home")
                time.sleep(5)
                
                # Oturum açık mı kontrol et
                if self.is_logged_in_check():
                    self.logger.info("Çerezler ile oturum açıldı")
                    self.is_logged_in = True
                    return True
            
            # Çerezler çalışmadıysa normal giriş yap
            self.logger.info("Normal giriş yapılıyor")
            self.driver.get("https://twitter.com/i/flow/login")
            time.sleep(3)
            
            # Email/kullanıcı adı giriş alanı
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
            )
            email_field.send_keys(os.environ.get('EMAIL_USER'))
            
            # İleri butonu
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']"))
            )
            next_button.click()
            time.sleep(2)
            
            # Kullanıcı adı doğrulama ekranı gelebilir
            try:
                username_verify = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='ocfEnterTextTextInput']"))
                )
                username_verify.send_keys(os.environ.get('TWITTER_USERNAME'))
                
                next_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']"))
                )
                next_button.click()
                time.sleep(2)
            except TimeoutException:
                self.logger.info("Kullanıcı adı doğrulama ekranı atlandı")
            
            # Şifre alanı
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']"))
            )
            password_field.send_keys(os.environ.get('TWITTER_PASSWORD'))
            
            # Giriş butonu
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Log in']"))
            )
            login_button.click()
            time.sleep(5)
            
            # Giriş başarılı mı kontrol et
            if self.is_logged_in_check():
                self.logger.info("Twitter'a başarıyla giriş yapıldı")
                self.is_logged_in = True
                self.save_cookies()
                return True
            else:
                self.logger.error("Twitter'a giriş yapılamadı")
                return False
                
        except Exception as e:
            self.logger.error(f"Twitter'a giriş yapılırken hata: {e}")
            return False
    
    def is_logged_in_check(self):
        """Oturum açık mı kontrol et"""
        try:
            # Ana sayfa elementlerini kontrol et
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-testid='AppTabBar_Home_Link']"))
            )
            return True
        except:
            return False
    
    def save_cookies(self):
        """Çerezleri kaydet"""
        try:
            os.makedirs('data', exist_ok=True)
            pickle.dump(self.driver.get_cookies(), open(self.cookies_file, "wb"))
            self.logger.info("Çerezler kaydedildi")
            return True
        except Exception as e:
            self.logger.error(f"Çerezler kaydedilirken hata: {e}")
            return False
    
    def load_cookies(self):
        """Çerezleri yükle"""
        try:
            if os.path.exists(self.cookies_file):
                self.driver.get("https://twitter.com")
                cookies = pickle.load(open(self.cookies_file, "rb"))
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
                self.logger.info("Çerezler yüklendi")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Çerezler yüklenirken hata: {e}")
            return False
    
    def post_tweet(self, content):
        """Tweet gönder"""
        if not self.is_logged_in:
            if not self.login():
                return False
        
        try:
            # Ana sayfaya git
            self.driver.get("https://twitter.com/home")
            time.sleep(3)
            
            # Tweet oluştur butonuna tıkla
            tweet_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-testid='SideNav_NewTweet_Button']"))
            )
            tweet_button.click()
            time.sleep(2)
            
            # Tweet içeriğini yaz
            tweet_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']"))
            )
            tweet_input.send_keys(content)
            time.sleep(1)
            
            # Tweet gönder butonuna tıkla
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='tweetButton']"))
            )
            post_button.click()
            time.sleep(3)
            
            self.logger.info("Tweet başarıyla gönderildi")
            return True
            
        except Exception as e:
            self.logger.error(f"Tweet gönderilirken hata: {e}")
            return False
    
    def reply_to_tweet(self, tweet_url, reply_content):
        """Tweet'e yanıt ver"""
        if not self.is_logged_in:
            if not self.login():
                return False
        
        try:
            # Tweet sayfasına git
            self.driver.get(tweet_url)
            time.sleep(5)
            
            # Yanıt butonuna tıkla
            reply_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='reply']"))
            )
            reply_button.click()
            time.sleep(2)
            
            # Yanıt içeriğini yaz
            reply_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']"))
            )
            reply_input.send_keys(reply_content)
            time.sleep(1)
            
            # Yanıt gönder butonuna tıkla
            reply_post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='tweetButton']"))
            )
            reply_post_button.click()
            time.sleep(3)
            
            self.logger.info(f"Yanıt başarıyla gönderildi: {tweet_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Yanıt gönderilirken hata: {e}")
            return False
    
    def follow_user(self, username):
        """Kullanıcıyı takip et"""
        if not self.is_logged_in:
            if not self.login():
                return False
        
        try:
            # Kullanıcı profiline git
            self.driver.get(f"https://twitter.com/{username}")
            time.sleep(3)
            
            # Takip et butonunu bul
            try:
                follow_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='follow']"))
                )
                follow_button.click()
                time.sleep(2)
                self.logger.info(f"@{username} takip edildi")
                return True
            except TimeoutException:
                self.logger.info(f"@{username} zaten takip ediliyor olabilir")
                return True
                
        except Exception as e:
            self.logger.error(f"@{username} takip edilirken hata: {e}")
            return False
    
    def get_latest_tweet(self, username):
        """Kullanıcının son tweet'ini al"""
        if not self.is_logged_in:
            if not self.login():
                return None
        
        try:
            # Kullanıcı profiline git
            self.driver.get(f"https://twitter.com/{username}")
            time.sleep(5)
            
            # İlk tweet'i bul
            tweet_elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
            )
            
            if not tweet_elements:
                self.logger.warning(f"@{username} için tweet bulunamadı")
                return None
            
            # İlk tweet'i seç
            first_tweet = tweet_elements[0]
            
            # Tweet metnini al
            tweet_text_element = first_tweet.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']")
            tweet_text = tweet_text_element.text
            
            # Tweet tarihini al
            time_element = first_tweet.find_element(By.CSS_SELECTOR, "time")
            tweet_time = time_element.get_attribute("datetime")
            
            # Tweet URL'sini al
            tweet_link = first_tweet.find_element(By.CSS_SELECTOR, "a[href*='/status/']")
            tweet_url = tweet_link.get_attribute("href")
            
            tweet_data = {
                'text': tweet_text,
                'time': tweet_time,
                'url': tweet_url,
                'username': username
            }
            
            self.logger.info(f"@{username} son tweet'i alındı")
            return tweet_data
            
        except Exception as e:
            self.logger.error(f"@{username} son tweet'i alınırken hata: {e}")
            return None
    
    def close(self):
        """Tarayıcıyı kapat"""
        if self.driver:
            self.driver.quit()
            self.logger.info("Tarayıcı kapatıldı")
