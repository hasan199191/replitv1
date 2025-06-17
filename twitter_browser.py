from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import pickle
import json
import logging
import random
import subprocess

class TwitterBrowser:
    def __init__(self):
        self.driver = None
        self.cookies_file = 'data/twitter_cookies.pkl'
        self.session_file = 'data/twitter_session.json'
        self.user_data_dir = '/tmp/chrome_profile'  # Render için /tmp kullan
        self.is_logged_in = False
        self.login_verified = False
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
        """Tarayıcıyı başlat - Persistent session ile"""
        try:
            # Data klasörlerini oluştur
            os.makedirs('data', exist_ok=True)
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            chrome_options = Options()
            
            # Render için headless mode
            if os.environ.get('IS_RENDER'):
                chrome_options.add_argument("--headless")
                chrome_options.binary_location = "/usr/bin/google-chrome"
            
            # Temel Chrome ayarları
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
            
            # PERSISTENT SESSION - Chrome profil klasörünü kullan
            chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")
            chrome_options.add_argument("--profile-directory=TwitterBot")
            
            # Anti-detection
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # ChromeDriver service oluştur
            if os.path.exists('/usr/bin/chromedriver'):
                service = Service('/usr/bin/chromedriver')
            else:
                service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Anti-detection script
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("✅ Browser initialized with persistent session")
            return True
                
        except Exception as e:
            self.logger.error(f"❌ Error initializing browser: {e}")
            return False
    
    def check_login_status(self):
        """Mevcut oturum durumunu kontrol et"""
        try:
            self.logger.info("🔍 Checking current login status...")
            
            # Ana sayfaya git
            self.driver.get("https://twitter.com/home")
            time.sleep(8)
            
            # Login durumunu kontrol et - birden fazla yöntem
            login_indicators = [
                # Tweet compose button
                "a[data-testid='SideNav_NewTweet_Button']",
                # Home timeline
                "[data-testid='primaryColumn']",
                # Profile menu
                "[data-testid='SideNav_AccountSwitcher_Button']",
                # Home tab
                "a[data-testid='AppTabBar_Home_Link']"
            ]
            
            for indicator in login_indicators:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, indicator))
                    )
                    if element:
                        self.logger.info(f"✅ Login confirmed! Found: {indicator}")
                        self.is_logged_in = True
                        self.login_verified = True
                        self.save_session_info()
                        return True
                except TimeoutException:
                    continue
            
            # URL kontrolü
            current_url = self.driver.current_url
            if "/home" in current_url and "login" not in current_url:
                self.logger.info("✅ Login confirmed by URL check")
                self.is_logged_in = True
                self.login_verified = True
                self.save_session_info()
                return True
            
            self.logger.info("❌ Not logged in - authentication required")
            return False
                
        except Exception as e:
            self.logger.error(f"❌ Error checking login status: {e}")
            return False
    
    def login(self):
        """Twitter'a giriş yap"""
        if not self.driver:
            if not self.initialize():
                return False
        
        # Önce mevcut session'ı kontrol et
        if self.check_login_status():
            return True
        
        try:
            self.logger.info("🚀 Starting Twitter login process...")
            
            # Login sayfasına git
            self.driver.get("https://twitter.com/i/flow/login")
            time.sleep(5)
            
            # Email alanını bul
            email_field = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
            )
            
            # Email gir
            email_field.clear()
            email_field.send_keys(os.environ.get('EMAIL_USER'))
            self.logger.info("📧 Email entered")
            time.sleep(2)
            
            # Next butonuna tıkla
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']"))
            )
            next_button.click()
            time.sleep(3)
            
            # Username verification kontrol et
            try:
                username_field = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='ocfEnterTextTextInput']"))
                )
                username_field.clear()
                username_field.send_keys(os.environ.get('TWITTER_USERNAME'))
                self.logger.info("👤 Username verification completed")
                
                next_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']"))
                )
                next_button.click()
                time.sleep(3)
            except TimeoutException:
                self.logger.info("⏭️ Username verification skipped")
            
            # Password alanını bul
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']"))
            )
            
            # Password gir
            password_field.clear()
            password_field.send_keys(os.environ.get('TWITTER_PASSWORD'))
            self.logger.info("🔐 Password entered")
            time.sleep(2)
            
            # Login butonuna tıkla
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Log in']"))
            )
            login_button.click()
            self.logger.info("🔑 Login button clicked")
            time.sleep(8)
            
            # Login başarılı mı kontrol et
            if self.check_login_status():
                self.logger.info("🎉 LOGIN SUCCESSFUL!")
                self.save_cookies()
                return True
            else:
                # Bir kez daha dene
                time.sleep(10)
                if self.check_login_status():
                    self.logger.info("🎉 LOGIN SUCCESSFUL (second attempt)!")
                    self.save_cookies()
                    return True
                else:
                    self.logger.error("❌ LOGIN FAILED")
                    return False
                
        except Exception as e:
            self.logger.error(f"❌ Login error: {e}")
            return False
    
    def save_cookies(self):
        """Çerezleri kaydet"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            self.logger.info("🍪 Cookies saved")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error saving cookies: {e}")
            return False
    
    def save_session_info(self):
        """Session bilgilerini kaydet"""
        try:
            session_info = {
                'login_time': time.time(),
                'current_url': self.driver.current_url,
                'page_title': self.driver.title,
                'session_active': True,
                'login_verified': True
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_info, f, indent=2)
            
            self.logger.info("💾 Session info saved")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error saving session: {e}")
            return False
    
    def post_tweet(self, content):
        """Tweet gönder"""
        if not self.is_logged_in:
            if not self.login():
                return False
        
        try:
            self.logger.info("📝 Posting tweet...")
            
            # Ana sayfaya git
            self.driver.get("https://twitter.com/home")
            time.sleep(5)
            
            # Tweet butonunu bul
            tweet_button = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-testid='SideNav_NewTweet_Button']"))
            )
            tweet_button.click()
            time.sleep(3)
            
            # Tweet alanını bul
            tweet_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']"))
            )
            
            # İçeriği yaz
            tweet_input.clear()
            tweet_input.send_keys(content)
            time.sleep(2)
            
            # Tweet gönder
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='tweetButton']"))
            )
            post_button.click()
            time.sleep(5)
            
            self.logger.info("✅ Tweet posted successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error posting tweet: {e}")
            return False
    
    def reply_to_tweet(self, tweet_url, reply_content):
        """Tweet'e yanıt ver"""
        if not self.is_logged_in:
            if not self.login():
                return False
        
        try:
            self.logger.info(f"💬 Replying to tweet: {tweet_url}")
            
            # Tweet sayfasına git
            self.driver.get(tweet_url)
            time.sleep(5)
            
            # Reply butonunu bul
            reply_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='reply']"))
            )
            reply_button.click()
            time.sleep(3)
            
            # Reply alanını bul
            reply_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']"))
            )
            
            # Reply içeriğini yaz
            reply_input.clear()
            reply_input.send_keys(reply_content)
            time.sleep(2)
            
            # Reply gönder
            reply_post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='tweetButton']"))
            )
            reply_post_button.click()
            time.sleep(5)
            
            self.logger.info("✅ Reply posted successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error posting reply: {e}")
            return False
    
    def follow_user(self, username):
        """Kullanıcıyı takip et"""
        if not self.is_logged_in:
            if not self.login():
                return False
        
        try:
            # Kullanıcı profiline git
            self.driver.get(f"https://twitter.com/{username}")
            time.sleep(5)
            
            # Follow butonunu bul
            try:
                follow_button = WebDriverWait(self.driver, 8).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='follow']"))
                )
                follow_button.click()
                time.sleep(2)
                self.logger.info(f"✅ Followed @{username}")
                return True
            except TimeoutException:
                self.logger.info(f"ℹ️ @{username} already followed")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Error following @{username}: {e}")
            return False
    
    def get_latest_tweet(self, username):
        """Kullanıcının son tweet'ini al"""
        if not self.is_logged_in:
            if not self.login():
                return None
        
        try:
            # Kullanıcı profiline git
            self.driver.get(f"https://twitter.com/{username}")
            time.sleep(8)
            
            # Tweet'leri bul
            tweet_elements = WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
            )
            
            if not tweet_elements:
                self.logger.warning(f"⚠️ No tweets found for @{username}")
                return None
            
            # İlk tweet'i al
            first_tweet = tweet_elements[0]
            
            # Tweet metnini al
            try:
                tweet_text_element = first_tweet.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']")
                tweet_text = tweet_text_element.text
            except NoSuchElementException:
                tweet_text = "No text content"
            
            # Tweet tarihini al
            try:
                time_element = first_tweet.find_element(By.CSS_SELECTOR, "time")
                tweet_time = time_element.get_attribute("datetime")
            except NoSuchElementException:
                tweet_time = None
            
            # Tweet URL'sini al
            try:
                tweet_link = first_tweet.find_element(By.CSS_SELECTOR, "a[href*='/status/']")
                tweet_url = tweet_link.get_attribute("href")
            except NoSuchElementException:
                tweet_url = None
            
            tweet_data = {
                'text': tweet_text,
                'time': tweet_time,
                'url': tweet_url,
                'username': username
            }
            
            self.logger.info(f"✅ Latest tweet retrieved for @{username}")
            return tweet_data
            
        except Exception as e:
            self.logger.error(f"❌ Error getting tweet for @{username}: {e}")
            return None
    
    def close(self):
        """Tarayıcıyı kapat"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("🔒 Browser closed")
            except Exception as e:
                self.logger.error(f"❌ Error closing browser: {e}")
