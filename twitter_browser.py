from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import asyncio
import time
import os
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict
from email_handler import EmailHandler

class TwitterBrowser:
    def __init__(self):
        self.playwright = None
        self.browser: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.user_data_dir = '/tmp/playwright_data'
        self.is_logged_in = False
        self.session_file = 'data/twitter_session.json'
        self.login_attempts = 0
        self.max_login_attempts = 3
        self.last_login_attempt = 0
        self.login_cooldown = 1800  # 30 dakika
        self.email_handler = EmailHandler()
        self.session_data = {}
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
    
    def can_attempt_login(self):
        """Login denemesi yapılabilir mi kontrol et"""
        current_time = time.time()
        
        if self.login_attempts >= self.max_login_attempts:
            if current_time - self.last_login_attempt < self.login_cooldown:
                remaining = self.login_cooldown - (current_time - self.last_login_attempt)
                self.logger.warning(f"⏳ Login cooldown active. Wait {remaining/60:.1f} minutes")
                return False
            else:
                self.login_attempts = 0
        
        return True
    
    def load_session_data(self):
        """Önceki session bilgilerini yükle"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    self.session_data = json.load(f)
                    self.logger.info("📂 Previous session data loaded")
                    return True
        except Exception as e:
            self.logger.warning(f"⚠️ Could not load session data: {e}")
        return False
    
    async def initialize(self):
        """Playwright + Chromium'u başlat - GELİŞTİRİLMİŞ SESSION MANAGEMENT"""
        try:
            self.logger.info("🚀 Initializing Playwright + Chromium with persistent session...")
            
            os.makedirs('data', exist_ok=True)
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            # Önceki session bilgilerini yükle
            self.load_session_data()
            
            self.playwright = await async_playwright().start()
            
            # PERSISTENT CONTEXT - Session'ı korur
            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,  # Render için headless
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-default-apps',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-automation',
                    '--disable-infobars',
                    '--start-maximized',
                    # Session persistence için ek ayarlar
                    '--disable-background-networking',
                    '--disable-sync',
                    '--disable-translate',
                    '--disable-ipc-flooding-protection'
                ]
            )
            
            # Anti-detection
            await self.browser.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """)
            
            self.page = await self.browser.new_page()
            
            self.logger.info("✅ Playwright + Chromium initialized with persistent session!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing Playwright: {e}")
            return False
    
    async def quick_login_check(self):
        """GÜÇLENDIRILMIŞ login durumu kontrolü"""
        try:
            self.logger.info("⚡ Enhanced login check...")
            
            # Home sayfasına git
            await self.page.goto("https://twitter.com/home", 
                               wait_until="domcontentloaded", 
                               timeout=15000)
            
            await asyncio.sleep(2)
            
            # Birden fazla login indicator kontrol et
            login_indicators = [
                'a[data-testid="SideNav_NewTweet_Button"]',  # Tweet butonu
                'div[data-testid="SideNav_AccountSwitcher_Button"]',  # Profil butonu
                'nav[role="navigation"]',  # Ana navigasyon
                'div[data-testid="primaryColumn"]',  # Ana kolon
                'div[data-testid="tweetTextarea_0"]',  # Tweet yazma alanı
                'aside[role="complementary"]'  # Yan panel
            ]
            
            login_confirmed = False
            for indicator in login_indicators:
                try:
                    element = await self.page.wait_for_selector(indicator, timeout=3000)
                    if element:
                        self.logger.info(f"✅ Login confirmed with indicator: {indicator}")
                        login_confirmed = True
                        break
                except:
                    continue
            
            if login_confirmed:
                # URL kontrolü de yap
                current_url = self.page.url
                if "/home" in current_url and "login" not in current_url:
                    self.logger.info("✅ Login confirmed by URL and elements!")
                    self.is_logged_in = True
                    await self.save_session_info()  # Session'ı kaydet
                    return True
            
            # Login sayfasında mıyız kontrol et
            current_url = self.page.url
            if any(path in current_url for path in ["/login", "/i/flow/login", "/oauth"]):
                self.logger.info("❌ On login page - not logged in")
                return False
            
            # Son çare: Sayfa title kontrolü
            try:
                title = await self.page.title()
                if "Home" in title or "Twitter" in title:
                    self.logger.info("✅ Login confirmed by page title!")
                    self.is_logged_in = True
                    await self.save_session_info()
                    return True
            except:
                pass
            
            self.logger.info("❌ Not logged in")
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️ Enhanced login check failed: {e}")
            return False
    
    async def check_login_status(self):
        """Login durumunu kontrol et - quick_login_check'in alias'ı"""
        return await self.quick_login_check()
    
    async def direct_login(self):
        """DİREKT ve HIZLI login süreci - GELİŞTİRİLMİŞ"""
        try:
            self.logger.info("⚡ Starting DIRECT login...")
            self.login_attempts += 1
            self.last_login_attempt = time.time()
        
            # Login sayfasına git
            await self.page.goto("https://twitter.com/i/flow/login", 
                                wait_until="domcontentloaded", 
                                timeout=15000)
        
            await asyncio.sleep(3)
        
            # 1. USERNAME GİR
            username = os.environ.get('TWITTER_USERNAME') or os.environ.get('EMAIL_USER')
            self.logger.info(f"⚡ Entering username: {username}")
        
            # Username alanını bul ve doldur
            username_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[type="text"]'
            ]
        
            username_entered = False
            for selector in username_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.fill(selector, username)
                    self.logger.info("⚡ Username entered")
                    username_entered = True
                    break
                except:
                    continue
        
            if not username_entered:
                self.logger.error("❌ Could not enter username")
                return False
        
            # Enter tuşuna bas (Next butonu yerine)
            await self.page.keyboard.press('Enter')
            self.logger.info("⚡ Enter pressed after username")
            await asyncio.sleep(3)
        
            # 2. EMAIL VERIFICATION KONTROLÜ (username sonrası)
            self.logger.info("🔍 Checking for email verification after username...")
        
            # Email verification alanı var mı kontrol et
            email_verification_needed = False
            try:
                # Email verification input alanını ara
                email_input = await self.page.wait_for_selector(
                    'input[data-testid="ocfEnterTextTextInput"]', 
                    timeout=5000
                )
                if email_input:
                    self.logger.info("📧 Email verification required after username")
                    email_verification_needed = True
                
                    # Email adresini gir
                    email_address = os.environ.get('EMAIL_USER')
                    await email_input.fill(email_address)
                    self.logger.info(f"📧 Email entered: {email_address}")
                
                    # Enter tuşuna bas
                    await self.page.keyboard.press('Enter')
                    await asyncio.sleep(3)
                
            except:
                self.logger.info("ℹ️ No email verification needed after username")
        
            # 3. USERNAME VERIFICATION (varsa - bazı durumlarda tekrar username ister)
            await self.handle_username_verification()
        
            # 4. PASSWORD GİR - GELİŞTİRİLMİŞ YAKLAŞIM
            password = os.environ.get('TWITTER_PASSWORD')
            self.logger.info("⚡ Looking for password field...")
        
            # Password alanını bekle ve direkt doldur
            password_entered = False
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[autocomplete="current-password"]'
            ]
        
            for selector in password_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=8000)
                    await self.page.fill(selector, password)
                    self.logger.info("⚡ Password entered")
                    password_entered = True
                    break
                except:
                    continue
        
            if not password_entered:
                self.logger.error("❌ Could not find or fill password field")
                return False
        
            # Hemen Enter tuşuna bas
            await self.page.keyboard.press('Enter')
            self.logger.info("⚡ Enter pressed for login")
            await asyncio.sleep(4)
        
            # 5. EMAIL VERIFICATION (login sonrası - eğer gerekirse)
            await self.handle_email_verification()
        
            # 6. LOGIN KONTROLÜ
            if await self.quick_login_check():
                self.logger.info("🎉 DIRECT LOGIN SUCCESSFUL!")
                self.login_attempts = 0
                await self.save_session_info()  # Session'ı kaydet
                return True
            else:
                # Bir kez daha dene
                await asyncio.sleep(3)
                if await self.quick_login_check():
                    self.logger.info("🎉 DIRECT LOGIN SUCCESSFUL (retry)!")
                    self.login_attempts = 0
                    await self.save_session_info()
                    return True
                else:
                    self.logger.error("❌ DIRECT LOGIN FAILED")
                    return False
            
        except Exception as e:
            self.logger.error(f"❌ Direct login error: {e}")
            return False
    
    async def handle_username_verification(self):
        """Username verification - HIZLI"""
        try:
            # Username verification alanı var mı?
            try:
                element = await self.page.wait_for_selector(
                    'input[data-testid="ocfEnterTextTextInput"]', 
                    timeout=3000
                )
                if element:
                    username = os.environ.get('TWITTER_USERNAME')
                    await element.fill(username)
                    self.logger.info(f"⚡ Username verification: {username}")
                    
                    # Enter tuşuna bas
                    await self.page.keyboard.press('Enter')
                    await asyncio.sleep(2)
                    return True
            except:
                pass
            
            return True
            
        except Exception as e:
            self.logger.warning(f"⚠️ Username verification error: {e}")
            return True
    
    async def handle_email_verification(self):
        """Email verification - EMAIL'DEN KOD AL - GELİŞTİRİLMİŞ"""
        try:
            self.logger.info("🔍 Checking for email verification...")

            # Email verification alanı var mı?
            verification_input = None
            verification_selectors = [
                'input[data-testid="ocfEnterTextTextInput"]',
                'input[placeholder*="code"]',
                'input[placeholder*="verification"]',
                'input[type="text"][maxlength="6"]',
                'input[type="text"][maxlength="8"]'
            ]
    
            for selector in verification_selectors:
                try:
                    verification_input = await self.page.wait_for_selector(selector, timeout=3000)
                    if verification_input:
                        self.logger.info(f"✅ Found verification input with selector: {selector}")
                        break
                except:
                    continue

            if not verification_input:
                self.logger.info("ℹ️ No email verification needed")
                return True

            self.logger.info("📧 Email verification required - getting code from email...")

            # Email'den doğrulama kodunu al
            self.logger.info("📧 Retrieving verification code from email...")
            verification_code = self.email_handler.get_twitter_verification_code(timeout=120)

            if verification_code:
                self.logger.info(f"✅ Got verification code: {verification_code}")
        
                # Kodu gir
                await verification_input.fill(verification_code)
                await asyncio.sleep(1)
        
                # Enter tuşuna bas
                await self.page.keyboard.press('Enter')
                self.logger.info("✅ Verification code submitted")
        
                await asyncio.sleep(4)
                return True
            else:
                self.logger.error("❌ Could not get verification code from email")
                self.logger.info("⏳ Trying to continue without verification code...")
            
                # Manuel giriş için biraz bekle
                await asyncio.sleep(30)
                return True
            
        except Exception as e:
            self.logger.error(f"❌ Email verification error: {e}")
            return True
    
    async def login(self):
        """Ana login metodu"""
        if not self.page:
            if not await self.initialize():
                return False
        
        if not self.can_attempt_login():
            return False
        
        # 1. Hızlı login kontrolü
        if await self.quick_login_check():
            return True
        
        # 2. Direkt login süreci
        return await self.direct_login()
    
    async def save_session_info(self):
        """Session bilgilerini kaydet - GELİŞTİRİLMİŞ"""
        try:
            current_time = time.time()
            current_url = self.page.url
            
            session_info = {
                'login_time': current_time,
                'last_check_time': current_time,
                'current_url': current_url,
                'session_active': True,
                'login_verified': True,
                'user_agent': await self.page.evaluate('navigator.userAgent'),
                'cookies_saved': True
            }
            
            # Session dosyasını kaydet
            with open(self.session_file, 'w') as f:
                json.dump(session_info, f, indent=2)
            
            self.session_data = session_info
            self.logger.info("💾 Enhanced session saved")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error saving session: {e}")
            return False
    
    async def post_tweet(self, content):
        """Tweet gönder - GELİŞTİRİLMİŞ"""
        if not self.is_logged_in:
            if not await self.login():
                return False
    
        try:
            self.logger.info("📝 Posting tweet...")
        
            # Home sayfasına git
            await self.page.goto("https://twitter.com/home", 
                                wait_until="domcontentloaded", 
                                timeout=15000)
            await asyncio.sleep(3)
        
            # Tweet compose alanını bul - birden fazla selector dene
            compose_selectors = [
                'div[data-testid="tweetTextarea_0"]',
                'div[contenteditable="true"][data-testid="tweetTextarea_0"]',
                'div[role="textbox"][data-testid="tweetTextarea_0"]',
                'div[contenteditable="true"]',
                'div[role="textbox"]'
            ]
        
            compose_element = None
            for selector in compose_selectors:
                try:
                    compose_element = await self.page.wait_for_selector(selector, timeout=5000)
                    if compose_element:
                        self.logger.info(f"✅ Found compose area with selector: {selector}")
                        break
                except:
                    continue
        
            if not compose_element:
                self.logger.error("❌ Could not find tweet compose area")
                return False
        
            # Tweet içeriğini yaz
            await compose_element.click()
            await asyncio.sleep(1)
            await compose_element.fill(content)
            await asyncio.sleep(2)
        
            self.logger.info(f"📝 Tweet content entered: {content[:50]}...")
        
            # Tweet gönder butonunu bul
            post_selectors = [
                'div[data-testid="tweetButton"]',
                'div[data-testid="tweetButtonInline"]',
                'button[data-testid="tweetButton"]',
                'button[data-testid="tweetButtonInline"]',
                '[role="button"][data-testid="tweetButton"]'
            ]
        
            post_button = None
            for selector in post_selectors:
                try:
                    post_button = await self.page.wait_for_selector(selector, timeout=3000)
                    if post_button:
                        # Butonun aktif olup olmadığını kontrol et
                        is_disabled = await post_button.get_attribute('aria-disabled')
                        if is_disabled != 'true':
                            self.logger.info(f"✅ Found active post button with selector: {selector}")
                            break
                        else:
                            self.logger.warning(f"⚠️ Post button found but disabled: {selector}")
                except:
                    continue
        
            if not post_button:
                self.logger.error("❌ Could not find active post button")
                # Klavye kısayolu dene
                self.logger.info("🔄 Trying keyboard shortcut...")
                await self.page.keyboard.press('Ctrl+Enter')
                await asyncio.sleep(3)
            else:
                # Butona tıkla
                await post_button.click()
                await asyncio.sleep(3)
        
            # Tweet gönderildi mi kontrol et - URL değişimi veya success mesajı
            current_url = self.page.url
            if "compose" not in current_url.lower():
                self.logger.info("✅ Tweet posted successfully!")
                return True
            else:
                self.logger.error("❌ Tweet posting may have failed")
                return False
        
        except Exception as e:
            self.logger.error(f"❌ Error posting tweet: {e}")
            return False
    
    async def reply_to_tweet(self, tweet_url, reply_content):
        """Tweet'e yanıt ver"""
        if not self.is_logged_in:
            if not await self.login():
                return False
        
        try:
            self.logger.info(f"💬 Replying to tweet...")
            
            await self.page.goto(tweet_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            # Reply butonuna tıkla
            try:
                await self.page.click('div[data-testid="reply"]')
            except:
                return False
            
            await asyncio.sleep(2)
            
            # Reply içeriğini yaz
            try:
                await self.page.fill('div[data-testid="tweetTextarea_0"]', reply_content)
            except:
                return False
            
            await asyncio.sleep(1)
            
            # Reply gönder
            try:
                await self.page.click('div[data-testid="tweetButton"]')
            except:
                await self.page.keyboard.press('Ctrl+Enter')
            
            await asyncio.sleep(2)
            
            self.logger.info("✅ Reply posted!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error posting reply: {e}")
            return False
    
    async def follow_user(self, username):
        """Kullanıcıyı takip et"""
        if not self.is_logged_in:
            if not await self.login():
                return False
        
        try:
            await self.page.goto(f"https://twitter.com/{username}", 
                                wait_until="domcontentloaded", 
                                timeout=15000)
            await asyncio.sleep(2)
            
            try:
                await self.page.click('div[data-testid="follow"]')
                await asyncio.sleep(2)
                self.logger.info(f"✅ Followed @{username}")
                return True
            except:
                self.logger.info(f"ℹ️ @{username} already followed")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Error following @{username}: {e}")
            return False
    
    async def get_latest_tweet(self, username):
        """Kullanıcının son tweet'ini al - GELİŞTİRİLMİŞ"""
        if not self.is_logged_in:
            if not await self.login():
                return None
    
        try:
            self.logger.info(f"🔍 Getting latest tweet for @{username}")
        
            # Kullanıcı profiline git
            await self.page.goto(f"https://twitter.com/{username}", 
                                wait_until="domcontentloaded", 
                                timeout=15000)
            await asyncio.sleep(4)
        
            # Tweet'leri bul - birden fazla selector dene
            tweet_selectors = [
                'article[data-testid="tweet"]',
                'div[data-testid="tweet"]',
                'article[role="article"]',
                'div[data-testid="cellInnerDiv"]'
            ]
        
            first_tweet = None
            for selector in tweet_selectors:
                try:
                    tweets = await self.page.query_selector_all(selector)
                    if tweets:
                        first_tweet = tweets[0]
                        self.logger.info(f"✅ Found tweets with selector: {selector}")
                        break
                except:
                    continue
        
            if not first_tweet:
                self.logger.warning(f"⚠️ No tweets found for @{username}")
                return None
        
            # Tweet bilgilerini al
            tweet_data = {}
        
            # Tweet metni
            try:
                text_selectors = [
                    'div[data-testid="tweetText"]',
                    'div[lang]',
                    'span[lang]'
                ]
            
                tweet_text = "No text"
                for selector in text_selectors:
                    try:
                        text_element = await first_tweet.query_selector(selector)
                        if text_element:
                            tweet_text = await text_element.inner_text()
                            break
                    except:
                        continue
            
                tweet_data['text'] = tweet_text
            
            except Exception as e:
                self.logger.warning(f"⚠️ Could not get tweet text: {e}")
                tweet_data['text'] = "No text"
        
            # Tweet zamanı
            try:
                time_selectors = [
                    'time',
                    'a[href*="/status/"] time',
                    '[datetime]'
                ]
            
                tweet_time = None
                for selector in time_selectors:
                    try:
                        time_element = await first_tweet.query_selector(selector)
                        if time_element:
                            tweet_time = await time_element.get_attribute("datetime")
                            break
                    except:
                        continue
            
                tweet_data['time'] = tweet_time
            
            except Exception as e:
                self.logger.warning(f"⚠️ Could not get tweet time: {e}")
                tweet_data['time'] = None
        
            # Tweet URL'i
            try:
                url_selectors = [
                    'a[href*="/status/"]',
                    'a[href*="/status/"][role="link"]'
                ]
            
                tweet_url = None
                for selector in url_selectors:
                    try:
                        link_element = await first_tweet.query_selector(selector)
                        if link_element:
                            tweet_url = await link_element.get_attribute("href")
                            if tweet_url and not tweet_url.startswith("https://"):
                                tweet_url = f"https://twitter.com{tweet_url}"
                            break
                    except:
                        continue
            
                tweet_data['url'] = tweet_url
            
            except Exception as e:
                self.logger.warning(f"⚠️ Could not get tweet URL: {e}")
                tweet_data['url'] = None
        
            tweet_data['username'] = username
        
            self.logger.info(f"✅ Tweet data retrieved for @{username}")
            self.logger.info(f"📝 Text: {tweet_data['text'][:100]}...")
            self.logger.info(f"🕐 Time: {tweet_data['time']}")
            self.logger.info(f"🔗 URL: {tweet_data['url']}")
        
            return tweet_data
        
        except Exception as e:
            self.logger.error(f"❌ Error getting tweet for @{username}: {e}")
            return None
    
    async def close(self):
        """Browser'ı kapat"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.logger.info("🔒 Browser closed")
        except Exception as e:
            self.logger.error(f"❌ Error closing browser: {e}")
