from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import asyncio
import time
import os
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict

class TwitterBrowserPlaywright:
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.user_data_dir = '/tmp/playwright_data'
        self.is_logged_in = False
        self.session_file = 'data/twitter_session.json'
        self.setup_logging()
        
    def setup_logging(self):
        """Loglama ayarlarını yapılandır"""
        self.logger = logging.getLogger('TwitterBrowserPlaywright')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    async def initialize(self):
        """Playwright + Chromium'u başlat"""
        try:
            self.logger.info("🚀 Initializing Playwright + Chromium...")
            
            # Data klasörlerini oluştur
            os.makedirs('data', exist_ok=True)
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            # Playwright'i başlat
            self.playwright = await async_playwright().start()
            
            # Browser'ı başlat - PERSISTENT CONTEXT ile
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Render için headless
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
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            # PERSISTENT CONTEXT oluştur - Bu session'ı koruyacak
            self.context = await self.browser.new_context(
                user_data_dir=self.user_data_dir,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            # Anti-detection
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                window.chrome = {
                    runtime: {},
                };
            """)
            
            # Yeni sayfa oluştur
            self.page = await self.context.new_page()
            
            self.logger.info("✅ Playwright + Chromium initialized with persistent context!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing Playwright: {e}")
            return False
    
    async def check_login_status(self):
        """Login durumunu kontrol et"""
        try:
            self.logger.info("🔍 Checking login status...")
            
            # Ana sayfaya git
            await self.page.goto("https://twitter.com/home", wait_until="networkidle")
            await asyncio.sleep(3)
            
            # Login indicator'ları kontrol et
            login_indicators = [
                'a[data-testid="SideNav_NewTweet_Button"]',
                '[data-testid="primaryColumn"]',
                'a[data-testid="AppTabBar_Home_Link"]',
                '[data-testid="SideNav_AccountSwitcher_Button"]'
            ]
            
            for indicator in login_indicators:
                try:
                    element = await self.page.wait_for_selector(indicator, timeout=5000)
                    if element:
                        self.logger.info(f"✅ Login confirmed! Found: {indicator}")
                        self.is_logged_in = True
                        await self.save_session_info()
                        return True
                except:
                    continue
            
            # URL kontrolü
            current_url = self.page.url
            if "/home" in current_url and "login" not in current_url:
                self.logger.info("✅ Login confirmed by URL check")
                self.is_logged_in = True
                await self.save_session_info()
                return True
            
            self.logger.info("❌ Not logged in - authentication required")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error checking login status: {e}")
            return False
    
    async def login(self):
        """Twitter'a giriş yap"""
        if not self.page:
            if not await self.initialize():
                return False
        
        # Önce mevcut session'ı kontrol et
        if await self.check_login_status():
            return True
        
        try:
            self.logger.info("🚀 Starting Twitter login process...")
            
            # Login sayfasına git
            await self.page.goto("https://twitter.com/i/flow/login", wait_until="networkidle")
            await asyncio.sleep(3)
            
            # Email alanını bul ve doldur
            email_selector = 'input[autocomplete="username"]'
            await self.page.wait_for_selector(email_selector, timeout=15000)
            await self.page.fill(email_selector, os.environ.get('EMAIL_USER'))
            self.logger.info("📧 Email entered")
            await asyncio.sleep(1)
            
            # Next butonuna tıkla
            next_button = 'xpath=//span[text()="Next"]'
            await self.page.click(next_button)
            await asyncio.sleep(3)
            
            # Username verification kontrol et
            try:
                username_field = await self.page.wait_for_selector('input[data-testid="ocfEnterTextTextInput"]', timeout=5000)
                if username_field:
                    await self.page.fill('input[data-testid="ocfEnterTextTextInput"]', os.environ.get('TWITTER_USERNAME'))
                    self.logger.info("👤 Username verification completed")
                    await self.page.click('xpath=//span[text()="Next"]')
                    await asyncio.sleep(3)
            except:
                self.logger.info("⏭️ Username verification skipped")
            
            # Password alanını bul ve doldur
            password_selector = 'input[name="password"]'
            await self.page.wait_for_selector(password_selector, timeout=10000)
            await self.page.fill(password_selector, os.environ.get('TWITTER_PASSWORD'))
            self.logger.info("🔐 Password entered")
            await asyncio.sleep(1)
            
            # Login butonuna tıkla
            login_button = 'xpath=//span[text()="Log in"]'
            await self.page.click(login_button)
            self.logger.info("🔑 Login button clicked")
            await asyncio.sleep(5)
            
            # Login başarılı mı kontrol et
            if await self.check_login_status():
                self.logger.info("🎉 LOGIN SUCCESSFUL!")
                return True
            else:
                # Bir kez daha dene
                await asyncio.sleep(5)
                if await self.check_login_status():
                    self.logger.info("🎉 LOGIN SUCCESSFUL (second attempt)!")
                    return True
                else:
                    self.logger.error("❌ LOGIN FAILED")
                    # Debug bilgisi
                    self.logger.info(f"Current URL: {self.page.url}")
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
                'login_verified': True
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
            await self.page.goto("https://twitter.com/home", wait_until="networkidle")
            await asyncio.sleep(3)
            
            # Tweet butonunu bul ve tıkla
            tweet_button = 'a[data-testid="SideNav_NewTweet_Button"]'
            await self.page.wait_for_selector(tweet_button, timeout=15000)
            await self.page.click(tweet_button)
            await asyncio.sleep(2)
            
            # Tweet alanını bul ve içeriği yaz
            tweet_input = 'div[data-testid="tweetTextarea_0"]'
            await self.page.wait_for_selector(tweet_input, timeout=10000)
            await self.page.fill(tweet_input, content)
            await asyncio.sleep(1)
            
            # Tweet gönder butonuna tıkla
            post_button = 'div[data-testid="tweetButton"]'
            await self.page.click(post_button)
            await asyncio.sleep(3)
            
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
            await self.page.goto(tweet_url, wait_until="networkidle")
            await asyncio.sleep(3)
            
            # Reply butonunu bul ve tıkla
            reply_button = 'div[data-testid="reply"]'
            await self.page.wait_for_selector(reply_button, timeout=10000)
            await self.page.click(reply_button)
            await asyncio.sleep(2)
            
            # Reply alanını bul ve içeriği yaz
            reply_input = 'div[data-testid="tweetTextarea_0"]'
            await self.page.wait_for_selector(reply_input, timeout=10000)
            await self.page.fill(reply_input, reply_content)
            await asyncio.sleep(1)
            
            # Reply gönder butonuna tıkla
            reply_post_button = 'div[data-testid="tweetButton"]'
            await self.page.click(reply_post_button)
            await asyncio.sleep(3)
            
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
            await self.page.goto(f"https://twitter.com/{username}", wait_until="networkidle")
            await asyncio.sleep(3)
            
            # Follow butonunu bul
            try:
                follow_button = await self.page.wait_for_selector('div[data-testid="follow"]', timeout=8000)
                if follow_button:
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
            # Kullanıcı profiline git
            await self.page.goto(f"https://twitter.com/{username}", wait_until="networkidle")
            await asyncio.sleep(5)
            
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
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.logger.info("🔒 Browser closed")
        except Exception as e:
            self.logger.error(f"❌ Error closing browser: {e}")
