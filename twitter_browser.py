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
    
    async def initialize(self):
        """Playwright + Chromium'u başlat"""
        try:
            self.logger.info("🚀 Initializing Playwright + Chromium...")
            
            os.makedirs('data', exist_ok=True)
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            self.playwright = await async_playwright().start()
            
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
                ]
            )
            
            # Anti-detection script
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
            
            self.logger.info("✅ Playwright + Chromium initialized!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing Playwright: {e}")
            return False
    
    async def quick_login_check(self):
        """HIZLI login durumu kontrolü"""
        try:
            self.logger.info("⚡ Quick login status check...")
            
            # Direkt home sayfasına git - timeout kısa
            await self.page.goto("https://twitter.com/home", 
                               wait_until="domcontentloaded", 
                               timeout=15000)
            
            # Sadece 2 saniye bekle
            await asyncio.sleep(2)
            
            # Hızlı indicator kontrolü - sadece en güvenilir olanları
            quick_indicators = [
                'a[data-testid="SideNav_NewTweet_Button"]',
                '[data-testid="tweetTextarea_0"]'
            ]
            
            for indicator in quick_indicators:
                try:
                    element = await self.page.wait_for_selector(indicator, timeout=2000)
                    if element:
                        self.logger.info("✅ Already logged in!")
                        self.is_logged_in = True
                        return True
                except:
                    continue
            
            # URL kontrolü
            current_url = self.page.url
            if "/home" in current_url and "login" not in current_url:
                self.logger.info("✅ Login confirmed by URL!")
                self.is_logged_in = True
                return True
            
            self.logger.info("❌ Not logged in - need to login")
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️ Quick check failed: {e}")
            return False
    
    async def fast_login(self):
        """HIZLI login süreci"""
        try:
            self.logger.info("⚡ Starting FAST login process...")
            self.login_attempts += 1
            self.last_login_attempt = time.time()
            
            # Login sayfasına git
            await self.page.goto("https://twitter.com/i/flow/login", 
                                wait_until="domcontentloaded", 
                                timeout=20000)
            
            # Kısa bekleme
            await asyncio.sleep(2)
            
            # 1. ADIM: Username/Email gir
            username = os.environ.get('TWITTER_USERNAME') or os.environ.get('EMAIL_USER')
            
            username_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[type="text"]'
            ]
            
            for selector in username_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.fill(selector, username)
                    self.logger.info(f"⚡ Username entered: {username}")
                    break
                except:
                    continue
            
            # Next butonuna tıkla veya Enter bas
            try:
                await self.page.click('xpath=//span[text()="Next"]')
                self.logger.info("⚡ Next clicked")
            except:
                try:
                    await self.page.keyboard.press('Enter')
                    self.logger.info("⚡ Enter pressed")
                except:
                    pass
            
            await asyncio.sleep(2)
            
            # 2. ADIM: Username verification (varsa)
            await self.handle_username_verification()
            
            # 3. ADIM: Password gir
            password = os.environ.get('TWITTER_PASSWORD')
            
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[autocomplete="current-password"]'
            ]
            
            for selector in password_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=8000)
                    await self.page.fill(selector, password)
                    self.logger.info("⚡ Password entered")
                    break
                except:
                    continue
            
            # Login butonuna tıkla
            try:
                await self.page.click('xpath=//span[text()="Log in"]')
                self.logger.info("⚡ Login clicked")
            except:
                try:
                    await self.page.keyboard.press('Enter')
                    self.logger.info("⚡ Enter pressed for login")
                except:
                    pass
            
            # Login sonrası bekleme
            await asyncio.sleep(3)
            
            # 4. ADIM: Email verification (varsa)
            await self.handle_email_verification()
            
            # 5. ADIM: Login kontrolü
            if await self.quick_login_check():
                self.logger.info("🎉 FAST LOGIN SUCCESSFUL!")
                self.login_attempts = 0
                return True
            else:
                # Bir kez daha dene
                await asyncio.sleep(3)
                if await self.quick_login_check():
                    self.logger.info("🎉 FAST LOGIN SUCCESSFUL (retry)!")
                    self.login_attempts = 0
                    return True
                else:
                    self.logger.error("❌ FAST LOGIN FAILED")
                    return False
                
        except Exception as e:
            self.logger.error(f"❌ Fast login error: {e}")
            return False
    
    async def handle_username_verification(self):
        """Username verification adımını işle"""
        try:
            # Username verification alanı var mı?
            verification_selectors = [
                'input[data-testid="ocfEnterTextTextInput"]',
                'input[placeholder*="username"]',
                'input[type="text"]'
            ]
            
            for selector in verification_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        username = os.environ.get('TWITTER_USERNAME')
                        await element.fill(username)
                        self.logger.info(f"⚡ Username verification: {username}")
                        
                        # Next butonuna tıkla
                        try:
                            await self.page.click('xpath=//span[text()="Next"]')
                        except:
                            await self.page.keyboard.press('Enter')
                        
                        await asyncio.sleep(2)
                        return True
                except:
                    continue
            
            return True
            
        except Exception as e:
            self.logger.warning(f"⚠️ Username verification error: {e}")
            return True
    
    async def handle_email_verification(self):
        """Email verification kodunu işle"""
        try:
            # Email verification alanı var mı?
            verification_selectors = [
                'input[data-testid="ocfEnterTextTextInput"]',
                'input[placeholder*="code"]',
                'input[type="text"]'
            ]
            
            verification_input = None
            for selector in verification_selectors:
                try:
                    verification_input = await self.page.wait_for_selector(selector, timeout=3000)
                    if verification_input:
                        self.logger.info("📧 Email verification required")
                        break
                except:
                    continue
            
            if not verification_input:
                self.logger.info("ℹ️ No email verification needed")
                return True
            
            # Gmail App Password kontrolü
            gmail_app_password = os.environ.get('GMAIL_APP_PASSWORD')
            if not gmail_app_password:
                self.logger.error("❌ GMAIL_APP_PASSWORD not found!")
                self.logger.info("⏳ Waiting 30 seconds for manual code entry...")
                await asyncio.sleep(30)
                return True
            
            # Email'den kod al
            self.logger.info("📧 Getting verification code from email...")
            verification_code = self.email_handler.get_twitter_verification_code(timeout=60)
            
            if verification_code:
                self.logger.info(f"✅ Got verification code: {verification_code}")
                
                await verification_input.fill(verification_code)
                await asyncio.sleep(1)
                
                # Submit
                try:
                    await self.page.click('xpath=//span[text()="Next"]')
                except:
                    await self.page.keyboard.press('Enter')
                
                await asyncio.sleep(3)
                self.logger.info("✅ Email verification completed")
                return True
            else:
                self.logger.error("❌ Could not get verification code")
                self.logger.info("⏳ Waiting 30 seconds for manual entry...")
                await asyncio.sleep(30)
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Email verification error: {e}")
            return True
    
    async def login(self):
        """Ana login metodu - OPTIMIZE EDİLMİŞ"""
        if not self.page:
            if not await self.initialize():
                return False
        
        if not self.can_attempt_login():
            return False
        
        # 1. Hızlı login kontrolü
        if await self.quick_login_check():
            return True
        
        # 2. Hızlı login süreci
        return await self.fast_login()
    
    async def save_session_info(self):
        """Session bilgilerini kaydet"""
        try:
            session_info = {
                'login_time': time.time(),
                'current_url': self.page.url,
                'session_active': True,
                'login_verified': True
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_info, f, indent=2)
            
            self.logger.info("💾 Session saved")
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
            
            await self.page.goto("https://twitter.com/home", 
                                wait_until="domcontentloaded", 
                                timeout=20000)
            await asyncio.sleep(2)
            
            # Tweet butonuna tıkla
            tweet_selectors = [
                'a[data-testid="SideNav_NewTweet_Button"]',
                '[data-testid="SideNav_NewTweet_Button"]'
            ]
            
            for selector in tweet_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.click(selector)
                    break
                except:
                    continue
            
            await asyncio.sleep(2)
            
            # Tweet içeriğini yaz
            tweet_selectors = [
                'div[data-testid="tweetTextarea_0"]',
                'div[role="textbox"]'
            ]
            
            for selector in tweet_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.fill(selector, content)
                    break
                except:
                    continue
            
            await asyncio.sleep(1)
            
            # Tweet gönder
            try:
                await self.page.click('div[data-testid="tweetButton"]')
            except:
                await self.page.keyboard.press('Ctrl+Enter')
            
            await asyncio.sleep(2)
            
            self.logger.info("✅ Tweet posted!")
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
            self.logger.info(f"💬 Replying to tweet...")
            
            await self.page.goto(tweet_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)
            
            # Reply butonuna tıkla
            try:
                await self.page.click('div[data-testid="reply"]')
            except:
                return False
            
            await asyncio.sleep(2)
            
            # Reply içeriğini yaz
            reply_selectors = [
                'div[data-testid="tweetTextarea_0"]',
                'div[role="textbox"]'
            ]
            
            for selector in reply_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.fill(selector, reply_content)
                    break
                except:
                    continue
            
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
                                timeout=20000)
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
        """Kullanıcının son tweet'ini al"""
        if not self.is_logged_in:
            if not await self.login():
                return None
        
        try:
            await self.page.goto(f"https://twitter.com/{username}", 
                                wait_until="domcontentloaded", 
                                timeout=20000)
            await asyncio.sleep(3)
            
            # İlk tweet'i bul
            first_tweet = await self.page.query_selector('article[data-testid="tweet"]')
            if not first_tweet:
                return None
            
            # Tweet bilgilerini al
            try:
                tweet_text_element = await first_tweet.query_selector('div[data-testid="tweetText"]')
                tweet_text = await tweet_text_element.inner_text() if tweet_text_element else "No text"
            except:
                tweet_text = "No text"
            
            try:
                time_element = await first_tweet.query_selector('time')
                tweet_time = await time_element.get_attribute("datetime") if time_element else None
            except:
                tweet_time = None
            
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
            
            self.logger.info(f"✅ Tweet retrieved for @{username}")
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
