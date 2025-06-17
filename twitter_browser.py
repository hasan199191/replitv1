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
import logging
import random
import subprocess

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
    
    def fix_chromedriver_path(self, driver_path):
        """webdriver-manager'ın yanlış path sorununu çöz"""
        try:
            # webdriver-manager bazen yanlış dosyayı işaret ediyor
            if 'THIRD_PARTY_NOTICES' in driver_path:
                # Doğru chromedriver dosyasını bul
                driver_dir = os.path.dirname(driver_path)
                for file in os.listdir(driver_dir):
                    if file == 'chromedriver' or file == 'chromedriver.exe':
                        correct_path = os.path.join(driver_dir, file)
                        self.logger.info(f"Fixed ChromeDriver path: {correct_path}")
                        return correct_path
                
                # chromedriver-linux64 klasörünü kontrol et
                linux64_dir = os.path.join(driver_dir, 'chromedriver-linux64')
                if os.path.exists(linux64_dir):
                    chromedriver_path = os.path.join(linux64_dir, 'chromedriver')
                    if os.path.exists(chromedriver_path):
                        self.logger.info(f"Found ChromeDriver in linux64 dir: {chromedriver_path}")
                        return chromedriver_path
            
            return driver_path
        except Exception as e:
            self.logger.error(f"Error fixing ChromeDriver path: {e}")
            return driver_path
    
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
                    return True
                except Exception as e:
                    self.logger.warning(f"System ChromeDriver failed: {e}")
            
            # 2. webdriver-manager ile dene
            try:
                self.logger.info("Trying webdriver-manager...")
                driver_path = ChromeDriverManager().install()
                
                # Path'i düzelt
                fixed_path = self.fix_chromedriver_path(driver_path)
                
                # Dosyanın executable olduğundan emin ol
                if os.path.exists(fixed_path):
                    os.chmod(fixed_path, 0o755)
                    service = Service(fixed_path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    self.logger.info(f"Successfully using webdriver-manager ChromeDriver: {fixed_path}")
                    return True
                else:
                    self.logger.error(f"ChromeDriver not found at: {fixed_path}")
                    
            except Exception as e:
                self.logger.error(f"webdriver-manager failed: {e}")
            
            # 3. Manuel download dene
            try:
                self.logger.info("Trying manual ChromeDriver download...")
                if chrome_version:
                    major_version = chrome_version.split('.')[0]
                    self.download_chromedriver(major_version)
                    
                    manual_path = '/tmp/chromedriver'
                    if os.path.exists(manual_path):
                        os.chmod(manual_path, 0o755)
                        service = Service(manual_path)
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        self.logger.info("Successfully using manually downloaded ChromeDriver")
                        return True
                        
            except Exception as e:
                self.logger.error(f"Manual download failed: {e}")
            
            raise Exception("All ChromeDriver initialization methods failed")
            
        except Exception as e:
            self.logger.error(f"Error initializing browser: {e}")
            return False
    
    def download_chromedriver(self, chrome_major_version):
        """Manuel ChromeDriver download"""
        try:
            import requests
            
            # Chrome for Testing API kullan
            api_url = f"https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_{chrome_major_version}"
            response = requests.get(api_url)
            
            if response.status_code == 200:
                version = response.text.strip()
                download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/linux64/chromedriver-linux64.zip"
                
                self.logger.info(f"Downloading ChromeDriver {version} from {download_url}")
                
                # Download ve extract
                import zipfile
                import io
                
                zip_response = requests.get(download_url)
                if zip_response.status_code == 200:
                    with zipfile.ZipFile(io.BytesIO(zip_response.content)) as zip_file:
                        # chromedriver dosyasını bul ve extract et
                        for file_info in zip_file.filelist:
                            if file_info.filename.endswith('chromedriver'):
                                with zip_file.open(file_info) as source:
                                    with open('/tmp/chromedriver', 'wb') as target:
                                        target.write(source.read())
                                self.logger.info("ChromeDriver downloaded successfully")
                                return True
                                
        except Exception as e:
            self.logger.error(f"Error downloading ChromeDriver: {e}")
            return False
    
    def login(self):
        """Twitter'a giriş yap"""
        if not self.driver:
            if not self.initialize():
                return False
        
        try:
            # Önce çerezleri kontrol et
            if self.load_cookies():
                self.logger.info("Cookies loaded, checking session")
                self.driver.get("https://twitter.com/home")
                time.sleep(5)
                
                # Oturum açık mı kontrol et
                if self.is_logged_in_check():
                    self.logger.info("Logged in using cookies")
                    self.is_logged_in = True
                    return True
            
            # Çerezler çalışmadıysa normal giriş yap
            self.logger.info("Performing normal login")
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
                self.logger.info("Username verification screen skipped")
            
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
                self.logger.info("Successfully logged in to Twitter")
                self.is_logged_in = True
                self.save_cookies()
                return True
            else:
                self.logger.error("Failed to log in to Twitter")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during Twitter login: {e}")
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
            self.logger.info("Cookies saved")
            return True
        except Exception as e:
            self.logger.error(f"Error saving cookies: {e}")
            return False
    
    def load_cookies(self):
        """Çerezleri yükle"""
        try:
            if os.path.exists(self.cookies_file):
                self.driver.get("https://twitter.com")
                cookies = pickle.load(open(self.cookies_file, "rb"))
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
                self.logger.info("Cookies loaded")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error loading cookies: {e}")
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
            
            self.logger.info("Tweet posted successfully")
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
            reply_input.send_keys(reply_content)
            time.sleep(1)
            
            # Yanıt gönder butonuna tıkla
            reply_post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='tweetButton']"))
            )
            reply_post_button.click()
            time.sleep(3)
            
            self.logger.info(f"Reply posted successfully: {tweet_url}")
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
                self.logger.info(f"@{username} followed")
                return True
            except TimeoutException:
                self.logger.info(f"@{username} already followed or button not found")
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
            
            self.logger.info(f"Latest tweet retrieved for @{username}")
            return tweet_data
            
        except Exception as e:
            self.logger.error(f"Error getting latest tweet for @{username}: {e}")
            return None
    
    def close(self):
        """Tarayıcıyı kapat"""
        if self.driver:
            self.driver.quit()
            self.logger.info("Browser closed")
