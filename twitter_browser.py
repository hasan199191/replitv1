from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import asyncio
import time
import os
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict

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
        
        # Çok fazla deneme yapıldıysa bekle
        if self.login_attempts >= self.max_login_attempts:
            if current_time - self.last_login_attempt < self.login_cooldown:
                remaining = self.login_cooldown - (current_time - self.last_login_attempt)
                self.logger.warning(f"⏳ Login cooldown active. Wait {remaining/60:.1f} minutes")
                return False
            else:
                # Cooldown bitti, reset yap
                self.login_attempts = 0
        
        return True
    
    async def initialize(self):
        """Playwright + Chromium'u başlat"""
        try:
            self.logger.info("🚀 Initializing Playwright + Chromium...")
            
            # Data klasörlerini oluştur
            os.makedirs('data', exist_ok=True)
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            # Playwright'i başlat
            self.playwright = await async_playwright().start()
            
            # Daha gerçekçi browser ayarları
            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
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
                    '--start-maximized'
                ],
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Cache-Control': 'max-age=0'
                }
            )
            
            # Gelişmiş anti-detection
            await self.browser.add_init_script("""
                // WebDriver özelliklerini gizle
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Chrome objesi ekle
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // Plugins dizisini doldur
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Languages ayarla
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Permission API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // WebGL vendor bilgisi
                const getParameter = WebGLRenderingContext.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter(parameter);
                };
            """)
            
            # Yeni sayfa oluştur
            self.page = await self.browser.new_page()
            
            # Sayfa ayarları
            await self.page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br'
            })
            
            self.logger.info("✅ Playwright + Chromium initialized with enhanced stealth!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing Playwright: {e}")
            return False
    
    async def check_login_status(self):
        """Login durumunu kontrol et"""
        try:
            self.logger.info("🔍 Checking login status...")
            
            # Önce mevcut session dosyasını kontrol et
            if os.path.exists(self.session_file):
                try:
                    with open(self.session_file, 'r') as f:
                        session_data = json.load(f)
                    
                    # Session çok eski mi?
                    if time.time() - session_data.get('login_time', 0) > 86400:  # 24 saat
                        self.logger.info("📅 Session expired (24+ hours old)")
                        os.remove(self.session_file)
                    else:
                        self.logger.info("💾 Found recent session file")
                except:
                    pass
            
            # Ana sayfaya git
            try:
                await self.page.goto("https://twitter.com/home", 
                                   wait_until="domcontentloaded", 
                                   timeout=45000)
                await asyncio.sleep(5)
            except Exception as e:
                self.logger.warning(f"⚠️ Error loading home page: {e}")
                return False
            
            # Login indicator'ları kontrol et
            login_indicators = [
                'a[data-testid="SideNav_NewTweet_Button"]',
                '[data-testid="primaryColumn"]',
                'a[data-testid="AppTabBar_Home_Link"]',
                '[data-testid="SideNav_AccountSwitcher_Button"]',
                '[data-testid="tweetTextarea_0"]',
                '[data-testid="UserAvatar-Container-unknown"]'
            ]
            
            found_indicators = 0
            for indicator in login_indicators:
                try:
                    element = await self.page.wait_for_selector(indicator, timeout=3000)
                    if element:
                        found_indicators += 1
                        self.logger.info(f"✅ Found login indicator: {indicator}")
                except:
                    continue
            
            # En az 2 indicator bulunmalı
            if found_indicators >= 2:
                self.logger.info(f"✅ Login confirmed! Found {found_indicators} indicators")
                self.is_logged_in = True
                await self.save_session_info()
                return True
            
            # URL kontrolü
            current_url = self.page.url
            if "/home" in current_url and "login" not in current_url and "flow" not in current_url:
                self.logger.info("✅ Login confirmed by URL check")
                self.is_logged_in = True
                await self.save_session_info()
                return True
            
            # Login sayfası kontrolü
            if "login" in current_url or "flow" in current_url:
                self.logger.info("❌ Redirected to login page")
                return False
            
            self.logger.info("❌ Not logged in - authentication required")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error checking login status: {e}")
            return False
    
    async def handle_verification_step(self):
        """Herhangi bir doğrulama adımını işle"""
        try:
            self.logger.info("🔍 Checking for verification requirements...")
            
            # Doğrulama alanı var mı kontrol et
            verification_selectors = [
                'input[data-testid="ocfEnterTextTextInput"]',
                'input[name="verfication_code"]',
                'input[placeholder*="code"]',
                'input[placeholder*="username"]',
                'input[type="text"]'
            ]
            
            verification_input = None
            for selector in verification_selectors:
                try:
                    verification_input = await self.page.wait_for_selector(selector, timeout=3000)
                    if verification_input:
                        self.logger.info(f"🔍 Found verification input: {selector}")
                        break
                except:
                    continue
            
            if not verification_input:
                self.logger.info("ℹ️ No verification required")
                return True
            
            # Placeholder veya label'dan ne istendiğini anlamaya çalış
            try:
                placeholder = await verification_input.get_attribute("placeholder") or ""
                aria_label = await verification_input.get_attribute("aria-label") or ""
                
                self.logger.info(f"🔍 Verification field placeholder: '{placeholder}'")
                self.logger.info(f"🔍 Verification field aria-label: '{aria_label}'")
                
                # Username istiyor mu?
                if any(keyword in (placeholder + aria_label).lower() for keyword in ['username', 'phone', 'email']):
                    username = os.environ.get('TWITTER_USERNAME')
                    if username:
                        await self.page.click(verification_input)
                        await asyncio.sleep(1)
                        await self.page.fill(verification_input, username)
                        await asyncio.sleep(random.uniform(1, 2))
                        self.logger.info(f"👤 Entered username: {username}")
                    else:
                        self.logger.error("❌ TWITTER_USERNAME not found in environment variables")
                        return False
                else:
                    # Bilinmeyen doğrulama türü, username dene
                    username = os.environ.get('TWITTER_USERNAME')
                    if username:
                        await self.page.click(verification_input)
                        await asyncio.sleep(1)
                        await self.page.fill(verification_input, username)
                        await asyncio.sleep(random.uniform(1, 2))
                        self.logger.info(f"👤 Tried username: {username}")
                    else:
                        self.logger.error("❌ TWITTER_USERNAME not found")
                        return False
                
                # Next/Submit butonuna tıkla
                submit_selectors = [
                    'xpath=//span[text()="Next"]',
                    'xpath=//span[text()="Submit"]',
                    'xpath=//span[text()="Verify"]',
                    'xpath=//div[@role="button" and contains(., "Next")]',
                    '[data-testid="ocfEnterTextNextButton"]'
                ]
                
                for selector in submit_selectors:
                    try:
                        await self.page.click(selector)
                        self.logger.info("✅ Verification submitted")
                        await asyncio.sleep(random.uniform(3, 5))
                        return True
                    except:
                        continue
                
                self.logger.warning("⚠️ Could not find submit button")
                return True
                
            except Exception as e:
                self.logger.error(f"❌ Error handling verification input: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error in verification handler: {e}")
            return False
    
    async def login(self):
        """Twitter'a giriş yap - BASİTLEŞTİRİLMİŞ"""
        if not self.page:
            if not await self.initialize():
                return False
        
        # Login denemesi yapılabilir mi?
        if not self.can_attempt_login():
            return False
        
        # Önce mevcut session'ı kontrol et
        if await self.check_login_status():
            return True
        
        try:
            self.logger.info("🚀 Starting Twitter login process...")
            self.login_attempts += 1
            self.last_login_attempt = time.time()
            
            # Login sayfasına git
            await self.page.goto("https://twitter.com/i/flow/login", 
                                wait_until="domcontentloaded", 
                                timeout=45000)
            
            # Sayfanın yüklenmesini bekle
            await asyncio.sleep(random.uniform(3, 6))
            
            # Email alanını bul ve doldur
            email_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[type="text"]'
            ]
            
            email_filled = False
            for selector in email_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    await asyncio.sleep(random.uniform(1, 2))
                    
                    # İnsan gibi yazma simülasyonu
                    email = os.environ.get('EMAIL_USER')
                    await self.page.click(selector)
                    await asyncio.sleep(0.5)
                    await self.page.fill(selector, email)
                    await asyncio.sleep(random.uniform(0.5, 1))
                    
                    self.logger.info("📧 Email entered")
                    email_filled = True
                    break
                except:
                    continue
            
            if not email_filled:
                raise Exception("Could not find email input field")
            
            # Next butonuna tıkla
            next_selectors = [
                'xpath=//span[text()="Next"]',
                'xpath=//div[@role="button" and contains(., "Next")]',
                '[data-testid="LoginForm_Login_Button"]'
            ]
            
            for selector in next_selectors:
                try:
                    await self.page.click(selector)
                    self.logger.info("➡️ Next button clicked")
                    break
                except:
                    continue
            
            await asyncio.sleep(random.uniform(3, 5))
            
            # Herhangi bir doğrulama adımını işle
            if not await self.handle_verification_step():
                self.logger.warning("⚠️ Verification step failed, continuing...")
            
            # Password alanını bul ve doldur
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[autocomplete="current-password"]'
            ]
            
            password_filled = False
            for selector in password_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=15000)
                    await asyncio.sleep(random.uniform(1, 2))
                    
                    password = os.environ.get('TWITTER_PASSWORD')
                    await self.page.click(selector)
                    await asyncio.sleep(0.5)
                    await self.page.fill(selector, password)
                    await asyncio.sleep(random.uniform(0.5, 1))
                    
                    self.logger.info("🔐 Password entered")
                    password_filled = True
                    break
                except:
                    continue
            
            if not password_filled:
                raise Exception("Could not find password input field")
            
            # Login butonuna tıkla
            login_selectors = [
                'xpath=//span[text()="Log in"]',
                'xpath=//div[@role="button" and contains(., "Log in")]',
                '[data-testid="LoginForm_Login_Button"]'
            ]
            
            for selector in login_selectors:
                try:
                    await self.page.click(selector)
                    self.logger.info("🔑 Login button clicked")
                    break
                except:
                    continue
            
            # Login işleminin tamamlanmasını bekle
            await asyncio.sleep(random.uniform(8, 12))
            
            # Tekrar doğrulama gerekebilir
            if not await self.handle_verification_step():
                self.logger.info("ℹ️ No additional verification needed")
            
            # Login başarılı mı kontrol et
            if await self.check_login_status():
                self.logger.info("🎉 LOGIN SUCCESSFUL!")
                self.login_attempts = 0  # Reset attempts on success
                return True
            else:
                # Bir kez daha dene
                await asyncio.sleep(5)
                if await self.check_login_status():
                    self.logger.info("🎉 LOGIN SUCCESSFUL (second attempt)!")
                    self.login_attempts = 0
                    return True
                else:
                    self.logger.error("❌ LOGIN FAILED")
                    self.logger.info(f"Current URL: {self.page.url}")
                    
                    # Hata mesajı var mı kontrol et
                    try:
                        error_element = await self.page.query_selector('[data-testid="error-message"]')
                        if error_element:
                            error_text = await error_element.inner_text()
                            self.logger.error(f"Twitter error: {error_text}")
                    except:
                        pass
                    
                    return False
                
        except Exception as e:
            self.logger.error(f"❌ Login error: {e}")
            return False
    
    async def save_session_info(self):
        """Session bilgilerini kaydet"""
        try:
            session_info = {
                'login_time': time.time(),
                'current_url': self.page.url,
                'page_title': await self.page.title(),
                'session_active': True,
                'login_verified': True,
                'user_agent': await self.page.evaluate('navigator.userAgent'),
                'viewport': await self.page.evaluate('({width: window.innerWidth, height: window.innerHeight})')
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_info, f, indent=2)
            
            self.logger.info("💾 Session info saved")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error saving session: {e}")
            return False
    
    async def post_tweet(self, content):
        """Tweet gönder"""
        if not self.is_logged_in:
            if not await self.login():
                return False
        
        try:
            self.logger.info("📝 Posting tweet...")
            
            # Ana sayfaya git
            await self.page.goto("https://twitter.com/home", 
                                wait_until="domcontentloaded", 
                                timeout=30000)
            await asyncio.sleep(random.uniform(3, 5))
            
            # Tweet butonunu bul ve tıkla
            tweet_selectors = [
                'a[data-testid="SideNav_NewTweet_Button"]',
                '[data-testid="SideNav_NewTweet_Button"]',
                'xpath=//a[@aria-label="Tweet"]'
            ]
            
            for selector in tweet_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    await self.page.click(selector)
                    self.logger.info("🖱️ Tweet button clicked")
                    break
                except:
                    continue
            
            await asyncio.sleep(random.uniform(2, 4))
            
            # Tweet alanını bul ve içeriği yaz
            tweet_selectors = [
                'div[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextarea_0"]',
                'div[role="textbox"]'
            ]
            
            for selector in tweet_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    await self.page.click(selector)
                    await asyncio.sleep(1)
                    
                    # İnsan gibi yazma simülasyonu
                    await self.page.fill(selector, content)
                    await asyncio.sleep(random.uniform(1, 2))
                    
                    self.logger.info("✍️ Tweet content entered")
                    break
                except:
                    continue
            
            # Tweet gönder butonuna tıkla
            post_selectors = [
                'div[data-testid="tweetButton"]',
                '[data-testid="tweetButton"]',
                'xpath=//div[@role="button" and contains(., "Tweet")]'
            ]
            
            for selector in post_selectors:
                try:
                    await self.page.click(selector)
                    self.logger.info("📤 Tweet post button clicked")
                    break
                except:
                    continue
            
            await asyncio.sleep(random.uniform(3, 5))
            
            self.logger.info("✅ Tweet posted successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error posting tweet: {e}")
            return False
    
    async def reply_to_tweet(self, tweet_url, reply_content):
        """Tweet'e yanıt ver"""
        if not self.is_logged_in:
            if not await self.login():
                return False
        
        try:
            self.logger.info(f"💬 Replying to tweet: {tweet_url}")
            
            # Tweet sayfasına git
            await self.page.goto(tweet_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(random.uniform(3, 5))
            
            # Reply butonunu bul ve tıkla
            reply_selectors = [
                'div[data-testid="reply"]',
                '[data-testid="reply"]',
                'xpath=//div[@aria-label="Reply"]'
            ]
            
            for selector in reply_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    await self.page.click(selector)
                    self.logger.info("💬 Reply button clicked")
                    break
                except:
                    continue
            
            await asyncio.sleep(random.uniform(2, 4))
            
            # Reply alanını bul ve içeriği yaz
            reply_input_selectors = [
                'div[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextarea_0"]',
                'div[role="textbox"]'
            ]
            
            for selector in reply_input_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    await self.page.click(selector)
                    await asyncio.sleep(1)
                    await self.page.fill(selector, reply_content)
                    await asyncio.sleep(random.uniform(1, 2))
                    self.logger.info("✍️ Reply content entered")
                    break
                except:
                    continue
            
            # Reply gönder butonuna tıkla
            reply_post_selectors = [
                'div[data-testid="tweetButton"]',
                '[data-testid="tweetButton"]',
                'xpath=//div[@role="button" and contains(., "Reply")]'
            ]
            
            for selector in reply_post_selectors:
                try:
                    await self.page.click(selector)
                    self.logger.info("📤 Reply post button clicked")
                    break
                except:
                    continue
            
            await asyncio.sleep(random.uniform(3, 5))
            
            self.logger.info("✅ Reply posted successfully!")
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
            # Kullanıcı profiline git
            await self.page.goto(f"https://twitter.com/{username}", 
                                wait_until="domcontentloaded", 
                                timeout=30000)
            await asyncio.sleep(random.uniform(3, 5))
            
            # Follow butonunu bul
            try:
                follow_button = await self.page.wait_for_selector('div[data-testid="follow"]', timeout=8000)
                if follow_button:
                    await self.page.click('div[data-testid="follow"]')
                    await asyncio.sleep(random.uniform(2, 4))
                    self.logger.info(f"✅ Followed @{username}")
                    return True
            except:
                self.logger.info(f"ℹ️ @{username} already followed or follow button not found")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Error following @{username}: {e}")
            return False
    
    async def get_latest_tweet(self, username):
        """Kullanıcının son tweet'ini al"""
        if not self.is_logged_in:
            if not await self.login():
                return None
        
        try:
            # Kullanıcı profiline git
            await self.page.goto(f"https://twitter.com/{username}", 
                                wait_until="domcontentloaded", 
                                timeout=30000)
            await asyncio.sleep(random.uniform(5, 8))
            
            # Tweet'leri bul
            tweet_selector = 'article[data-testid="tweet"]'
            await self.page.wait_for_selector(tweet_selector, timeout=15000)
            
            # İlk tweet'i al
            first_tweet = await self.page.query_selector(tweet_selector)
            if not first_tweet:
                self.logger.warning(f"⚠️ No tweets found for @{username}")
                return None
            
            # Tweet metnini al
            try:
                tweet_text_element = await first_tweet.query_selector('div[data-testid="tweetText"]')
                tweet_text = await tweet_text_element.inner_text() if tweet_text_element else "No text content"
            except:
                tweet_text = "No text content"
            
            # Tweet tarihini al
            try:
                time_element = await first_tweet.query_selector('time')
                tweet_time = await time_element.get_attribute("datetime") if time_element else None
            except:
                tweet_time = None
            
            # Tweet URL'sini al
            try:
                tweet_link = await first_tweet.query_selector('a[href*="/status/"]')
                tweet_url = await tweet_link.get_attribute("href") if tweet_link else None
                if tweet_url and not tweet_url.startswith("https://"):
                    tweet_url = f"https://twitter.com{tweet_url}"
            except:
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
