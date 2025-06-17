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
        self.user_data_dir = 'data/chrome_profile'
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
    
    def get_chrome_version(self):
        """Chrome versiyonunu al"""
        try:
            result = subprocess.run(['google-chrome', '--version'], 
                                  capture_output=True, text=True)
            version = result.stdout.strip().split()[-1]
            self.logger.info(f"Chrome version detected: {version}")
            return version
        except Exception as e:
            self.logger.error(f"Error getting Chrome version: {e}")
            return None
    
    def initialize(self):
        """Tarayıcıyı başlat - Session persistence ile"""
        try:
            # Data klasörlerini oluştur
            os.makedirs('data', exist_ok=True)
            os.makedirs(self.user_data_dir, exist_ok=True)
            
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
            
            # SESSION PERSISTENCE - Chrome profil klasörünü kullan
            chrome_options.add_argument(f"--user-data-dir={os.path.abspath(self.user_data_dir)}")
            chrome_options.add_argument("--profile-directory=Default")
            
            # Render.com için özel ayarlar
            if os.environ.get('IS_RENDER'):
                chrome_options.add_argument("--disable-background-timer-throttling")
                chrome_options.add_argument("--disable-backgrounding-occluded-windows")
                chrome_options.add_argument("--disable-renderer-backgrounding")
                chrome_options.add_argument("--disable-features=TranslateUI")
                chrome_options.add_argument("--disable-ipc-flooding-protection")
                chrome_options.binary_location = "/usr/bin/google-chrome"
            
            # ChromeDriver service oluştur
            if os.path.exists('/usr/bin/chromedriver'):
                service = Service('/usr/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.logger.info("Successfully using system ChromeDriver with persistent session")
                return True
            else:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.logger.info("Successfully using webdriver-manager ChromeDriver with persistent session")
                return True
                
        except Exception as e:
            self.logger.error(f"Error initializing browser: {e}")
            return False
    
    def check_login_status(self):
        """Mevcut oturum durumunu kontrol et"""
        try:
            self.logger.info("Checking current login status...")
            self.driver.get("https://twitter.com/home")
            time.sleep(5)
            
            # Ana sayfa elementlerini kontrol et
            try:
                # Home timeline'ı kontrol et
                WebDriverWait(self.driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-testid='AppTabBar_Home_Link']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Home timeline']"))
                    )
                )
                self.logger.info("✅ Already logged in - session is active!")
                self.is_logged_in = True
                self.save_session_info()
                return True
            except TimeoutException:
                self.logger.info("❌ Not logged in - need to authenticate")
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking login status: {e}")
            return False
    
    def login(self):
        """Twitter'a giriş yap - Session persistence ile"""
        if not self.driver:
            if not self.initialize():
                return False
        
        # Önce mevcut oturum durumunu kontrol et
        if self.check_login_status():
            return True
        
        try:
            self.logger.info("Starting fresh login process...")
            
            # Login sayfasına git
            self.driver.get("https://twitter.com/i/flow/login")
            time.sleep(3)
            
            # Email/kullanıcı adı giriş alanı - Birden fazla selector dene
            email_field = None
            selectors = [
                "input[autocomplete='username']",
                "input[name='text']",
                "input[data-testid='ocfEnterTextTextInput']",
                "input[placeholder*='email']",
                "input[placeholder*='username']"
            ]
            
            for selector in selectors:
                try:
                    email_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    self.logger.info(f"Found email field with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not email_field:
                self.logger.error("Could not find email input field")
                return False
            
            email_field.clear()
            email_field.send_keys(os.environ.get('EMAIL_USER'))
            time.sleep(1)
            
            # İleri butonu - Birden fazla selector dene
            next_selectors = [
                "//span[text()='Next']",
                "//div[@role='button' and contains(text(), 'Next')]",
                "[data-testid='ocfEnterTextNextButton']",
                "//button[contains(text(), 'Next')]"
            ]
            
            next_button = None
            for selector in next_selectors:
                try:
                    if selector.startswith("//"):
                        next_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        next_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    self.logger.info(f"Found next button with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not next_button:
                self.logger.error("Could not find next button")
                return False
                
            next_button.click()
            time.sleep(3)
            
            # Kullanıcı adı doğrulama ekranı kontrol et
            try:
                username_verify = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='ocfEnterTextTextInput']"))
                )
                self.logger.info("Username verification screen detected")
                username_verify.clear()
                username_verify.send_keys(os.environ.get('TWITTER_USERNAME'))
                
                next_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']"))
                )
                next_button.click()
                time.sleep(3)
            except TimeoutException:
                self.logger.info("Username verification screen skipped")
            
            # Şifre alanı - Birden fazla selector dene
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "input[autocomplete='current-password']"
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    self.logger.info(f"Found password field with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not password_field:
                self.logger.error("Could not find password input field")
                return False
            
            password_field.clear()
            password_field.send_keys(os.environ.get('TWITTER_PASSWORD'))
            time.sleep(1)
            
            # Giriş butonu - Birden fazla selector dene
            login_selectors = [
                "//span[text()='Log in']",
                "//div[@role='button' and contains(text(), 'Log in')]",
                "[data-testid='LoginForm_Login_Button']",
                "//button[contains(text(), 'Log in')]"
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    if selector.startswith("//"):
                        login_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        login_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    self.logger.info(f"Found login button with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not login_button:
                self.logger.error("Could not find login button")
                return False
                
            login_button.click()
            time.sleep(5)
            
            # Giriş başarılı mı kontrol et
            if self.check_login_status():
                self.logger.info("✅ Successfully logged in to Twitter!")
                self.save_cookies()
                self.save_session_info()
                return True
            else:
                self.logger.error("❌ Login failed - could not verify successful login")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during Twitter login: {e}")
            return False
    
    def save_cookies(self):
        """Çerezleri kaydet"""
        try:
            os.makedirs('data', exist_ok=True)
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            self.logger.info("Cookies saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error saving cookies: {e}")
            return False
    
    def save_session_info(self):
        """Session bilgilerini kaydet"""
        try:
            session_info = {
                'login_time': time.time(),
                'user_agent': self.driver.execute_script("return navigator.userAgent;"),
                'current_url': self.driver.current_url,
                'session_active': True
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_info, f, indent=2)
            
            self.logger.info("Session info saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error saving session info: {e}")
            return False
    
    def load_session_info(self):
        """Session bilgilerini yükle"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    session_info = json.load(f)
                
                # Session 24 saatten eski mi kontrol et
                if time.time() - session_info.get('login_time', 0) > 86400:  # 24 saat
                    self.logger.info("Session expired (older than 24 hours)")
                    return False
                
                self.logger.info("Session info loaded successfully")
                return session_info
            return False
        except Exception as e:
            self.logger.error(f"Error loading session info: {e}")
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
            
            # Tweet oluştur butonuna tıkla - Birden fazla selector dene
            tweet_selectors = [
                "a[data-testid='SideNav_NewTweet_Button']",
                "[data-testid='tweetButtonInline']",
                "//a[@aria-label='Tweet']",
                "//div[@role='button' and contains(@aria-label, 'Tweet')]"
            ]
            
            tweet_button = None
            for selector in tweet_selectors:
                try:
                    if selector.startswith("//"):
                        tweet_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        tweet_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    break
                except TimeoutException:
                    continue
            
            if not tweet_button:
                self.logger.error("Could not find tweet button")
                return False
                
            tweet_button.click()
            time.sleep(2)
            
            # Tweet içeriğini yaz - Birden fazla selector dene
            text_selectors = [
                "div[data-testid='tweetTextarea_0']",
                "div[role='textbox'][aria-label*='Tweet']",
                "div[contenteditable='true'][role='textbox']"
            ]
            
            tweet_input = None
            for selector in text_selectors:
                try:
                    tweet_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not tweet_input:
                self.logger.error("Could not find tweet input field")
                return False
            
            tweet_input.clear()
            tweet_input.send_keys(content)
            time.sleep(2)
            
            # Tweet gönder butonuna tıkla
            post_selectors = [
                "div[data-testid='tweetButton']",
                "div[data-testid='tweetButtonInline']",
                "//div[@role='button' and contains(text(), 'Tweet')]"
            ]
            
            post_button = None
            for selector in post_selectors:
                try:
                    if selector.startswith("//"):
                        post_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        post_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    break
                except TimeoutException:
                    continue
            
            if not post_button:
                self.logger.error("Could not find post button")
                return False
                
            post_button.click()
            time.sleep(3)
            
            self.logger.info("✅ Tweet posted successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error posting tweet: {e}")
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
            reply_input.clear()
            reply_input.send_keys(reply_content)
            time.sleep(1)
            
            # Yanıt gönder butonuna tıkla
            reply_post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='tweetButton']"))
            )
            reply_post_button.click()
            time.sleep(3)
            
            self.logger.info(f"✅ Reply posted successfully: {tweet_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error posting reply: {e}")
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
                self.logger.info(f"✅ @{username} followed")
                return True
            except TimeoutException:
                self.logger.info(f"ℹ️ @{username} already followed or button not found")
                return True
                
        except Exception as e:
            self.logger.error(f"Error following @{username}: {e}")
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
                self.logger.warning(f"No tweets found for @{username}")
                return None
            
            # İlk tweet'i seç
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
            self.logger.error(f"Error getting latest tweet for @{username}: {e}")
            return None
    
    def close(self):
        """Tarayıcıyı kapat"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser closed")
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")
