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
        self.max_login_attempts = 2  # Azaltıldı
        self.last_login_attempt = 0
        self.login_cooldown = 900  # 15 dakika (azaltıldı)
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
                    '--memory-pressure-off',
                    '--max_old_space_size=4096',
                    '--single-process'
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
            
            self.logger.info("✅ Playwright + Chromium initialized!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing Playwright: {e}")
            return False
    
    async def quick_login_check(self):
        """HIZLI login durumu kontrolü - OPTIMIZE EDİLDİ"""
        try:
            self.logger.info("⚡ Quick login check...")
            
            # Mevcut URL'yi kontrol et
            current_url = self.page.url
            if "/home" in current_url and "login" not in current_url:
                self.logger.info("✅ Already logged in (URL check)!")
                self.is_logged_in = True
                return True
            
            # Home sayfasına git - kısa timeout
            await self.page.goto("https://twitter.com/home", 
                               wait_until="domcontentloaded", 
                               timeout=8000)  # Azaltıldı
            
            await asyncio.sleep(1)
            
            # Tweet butonu var mı kontrol et - kısa timeout
            try:
                element = await self.page.wait_for_selector(
                    'a[data-testid="SideNav_NewTweet_Button"]', 
                    timeout=2000  # Azaltıldı
                )
                if element:
                    self.logger.info("✅ Already logged in!")
                    self.is_logged_in = True
                    return True
            except:
                pass
            
            # URL kontrolü tekrar
            current_url = self.page.url
            if "/home" in current_url and "login" not in current_url:
                self.logger.info("✅ Login confirmed by URL!")
                self.is_logged_in = True
                return True
            
            self.logger.info("❌ Not logged in")
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️ Quick check failed: {e}")
            return False
    
    async def direct_login(self):
        """DİREKT ve HIZLI login süreci - OPTIMIZE EDİLDİ"""
        try:
            self.logger.info("⚡ Starting DIRECT login...")
            self.login_attempts += 1
            self.last_login_attempt = time.time()
            
            # Login sayfasına git
            await self.page.goto("https://twitter.com/i/flow/login", 
                                wait_until="domcontentloaded", 
                                timeout=10000)  # Azaltıldı
            
            await asyncio.sleep(2)
            
            # 1. USERNAME GİR
            username = os.environ.get('TWITTER_USERNAME') or os.environ.get('EMAIL_ADDRESS')
            self.logger.info(f"⚡ Entering username: {username}")
            
            # Username alanını bul ve doldur - sadece en yaygın selector
            try:
                await self.page.wait_for_selector('input[autocomplete="username"]', timeout=5000)
                await self.page.fill('input[autocomplete="username"]', username)
                self.logger.info("⚡ Username entered")
            except:
                try:
                    await self.page.wait_for_selector('input[type="text"]', timeout=3000)
                    await self.page.fill('input[type="text"]', username)
                    self.logger.info("⚡ Username entered (fallback)")
                except:
                    self.logger.error("❌ Could not find username field")
                    return False
            
            # Enter tuşuna bas
            await self.page.keyboard.press('Enter')
            self.logger.info("⚡ Enter pressed")
            await asyncio.sleep(2)
            
            # 2. PASSWORD GİR - SADECE EN YAYGINI DENE
            password = os.environ.get('TWITTER_PASSWORD')
            self.logger.info("⚡ Looking for password field...")

            try:
                # Sadece en yaygın password selector'ı dene
                password_element = await self.page.wait_for_selector('input[type="password"]', timeout=8000)
                
                if password_element:
                    await password_element.click()
                    await asyncio.sleep(1)
                    await password_element.fill(password)
                    self.logger.info("⚡ Password entered successfully")
                    
                    # Enter tuşuna bas
                    await self.page.keyboard.press('Enter')
                    self.logger.info("⚡ Enter pressed for login")
                else:
                    self.logger.error("❌ Could not find password field")
                    return False
                        
            except Exception as e:
                self.logger.error(f"❌ Password field error: {e}")
                return False
            
            # Login sonrası bekleme
            await asyncio.sleep(3)
            
            # LOGIN KONTROLÜ
            if await self.quick_login_check():
                self.logger.info("🎉 DIRECT LOGIN SUCCESSFUL!")
                self.login_attempts = 0
                return True
            else:
                self.logger.error("❌ DIRECT LOGIN FAILED")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Direct login error: {e}")
            return False
    
    async def login(self):
        """Ana login metodu - OPTIMIZE EDİLDİ"""
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
    
    async def post_tweet(self, content):
        """Tweet gönder - GELİŞTİRİLMİŞ COMPOSE DETECTION"""
        if not self.is_logged_in:
            if not await self.login():
                return False

        try:
            self.logger.info("📝 Posting tweet...")
        
            # Home sayfasına git
            await self.page.goto("https://twitter.com/home", 
                        wait_until="domcontentloaded", 
                        timeout=10000)
        await asyncio.sleep(3)  # Biraz daha bekle
    
        # Method 1: Direkt compose area ara
        self.logger.info("🔍 Method 1: Looking for compose area directly...")
        compose_element = await self.find_compose_area_direct()

        # Method 2: Tweet butonuna tıklayarak compose area aç
        if not compose_element:
            self.logger.info("🔄 Method 1 failed, trying to click tweet button...")
            compose_element = await self.find_compose_area_via_button()

        # Method 3: Klavye kısayolu ile compose area aç
        if not compose_element:
            self.logger.info("🔄 Method 2 failed, trying keyboard shortcut...")
            compose_element = await self.find_compose_area_via_shortcut()

        # Method 4: Sayfayı yenile ve tekrar dene
        if not compose_element:
            self.logger.info("🔄 Method 3 failed, refreshing page...")
            await self.page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(3)
            compose_element = await self.find_compose_area_direct()

        if not compose_element:
            self.logger.error("❌ Could not find tweet compose area with any method")
            return False

        # Tweet içeriğini yaz
        self.logger.info("✅ Found compose area, entering content...")
        await compose_element.click()
        await asyncio.sleep(1)
        
        # İçeriği temizle ve yaz
        await compose_element.fill('')
        await asyncio.sleep(0.5)
        await compose_element.type(content, delay=50)  # Daha yavaş yazma
        await asyncio.sleep(2)

        self.logger.info(f"📝 Tweet content entered: {content[:50]}...")

        # Tweet gönder butonunu bul ve tıkla
        if await self.click_post_button():
            self.logger.info("✅ Tweet posted successfully!")
            return True
        else:
            self.logger.error("❌ Failed to click post button")
            return False

    except Exception as e:
        self.logger.error(f"❌ Error posting tweet: {e}")
        return False

    async def find_compose_area_direct(self):
        """Direkt compose area bul"""
        try:
            # X.com güncel selectors - 2024
            selectors = [
                # Ana compose area
                'div[data-testid="tweetTextarea_0"]',
                'div[contenteditable="true"][data-testid="tweetTextarea_0"]',
                
                # Genel contenteditable alanlar
                'div[contenteditable="true"][role="textbox"]',
                'div[contenteditable="true"][aria-label*="Post"]',
                'div[contenteditable="true"][aria-label*="Tweet"]',
                'div[contenteditable="true"][aria-label*="What"]',
                
                # Placeholder ile
                'div[placeholder*="What is happening"]',
                'div[placeholder*="What\'s happening"]',
                
                # CSS class ile
                '.public-DraftEditor-content',
                '.notranslate.public-DraftEditor-content',
                
                # Genel fallback
                'div[contenteditable="true"]',
                'div[role="textbox"]'
            ]
            
            for selector in selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        # Element gerçekten editable mi kontrol et
                        is_editable = await element.evaluate('el => el.contentEditable === "true" || el.tagName === "TEXTAREA"')
                        if is_editable:
                            self.logger.info(f"✅ Found compose area: {selector}")
                            return element
            except:
                continue
            
            return None
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error in find_compose_area_direct: {e}")
            return None

    async def find_compose_area_via_button(self):
        """Tweet butonuna tıklayarak compose area bul"""
        try:
            # Tweet butonları
            button_selectors = [
                'a[data-testid="SideNav_NewTweet_Button"]',
                'div[data-testid="SideNav_NewTweet_Button"]',
                'button[data-testid="SideNav_NewTweet_Button"]',
                'a[href="/compose/tweet"]',
                'a[href="/compose/post"]',
                'button[aria-label*="Post"]',
                'button[aria-label*="Tweet"]',
                'div[role="button"][aria-label*="Post"]',
                'div[role="button"][aria-label*="Tweet"]'
            ]
            
            for selector in button_selectors:
                try:
                    button = await self.page.wait_for_selector(selector, timeout=2000)
                    if button:
                        await button.click()
                        await asyncio.sleep(2)
                        
                        # Compose area'yı ara
                        compose_element = await self.find_compose_area_direct()
                        if compose_element:
                            self.logger.info(f"✅ Found compose area after clicking: {selector}")
                            return compose_element
            except:
                continue
            
            return None
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error in find_compose_area_via_button: {e}")
        return None

    async def find_compose_area_via_shortcut(self):
        """Klavye kısayolu ile compose area bul"""
        try:
            # X.com'da 'n' tuşu compose açar
            await self.page.keyboard.press('n')
            await asyncio.sleep(2)
            
            # Compose area'yı ara
            compose_element = await self.find_compose_area_direct()
            if compose_element:
                self.logger.info("✅ Found compose area via keyboard shortcut")
                return compose_element
            
            return None
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error in find_compose_area_via_shortcut: {e}")
            return None

    async def click_post_button(self):
        """Post butonunu bul ve tıkla"""
        try:
            # Post buton selectors
            post_selectors = [
                'div[data-testid="tweetButton"]',
                'button[data-testid="tweetButton"]',
                'div[data-testid="tweetButtonInline"]',
                'button[data-testid="tweetButtonInline"]',
                'div[role="button"][data-testid="tweetButton"]',
                'button[role="button"][data-testid="tweetButton"]',
                'div[aria-label*="Post"]',
                'button[aria-label*="Post"]',
                'div[aria-label*="Tweet"]',
                'button[aria-label*="Tweet"]'
            ]
            
            for selector in post_selectors:
                try:
                    button = await self.page.wait_for_selector(selector, timeout=2000)
                    if button:
                        # Butonun aktif olup olmadığını kontrol et
                        is_disabled = await button.get_attribute('aria-disabled')
                        is_clickable = await button.evaluate('el => !el.disabled && el.offsetParent !== null')
                        
                        if is_disabled != 'true' and is_clickable:
                            await button.click()
                            await asyncio.sleep(2)
                            self.logger.info(f"✅ Clicked post button: {selector}")
                            return True
            except:
                continue

        # Klavye kısayolu dene
        self.logger.info("🔄 Trying keyboard shortcut Ctrl+Enter...")
        await self.page.keyboard.press('Control+Enter')
        await asyncio.sleep(2)
        return True
        
    except Exception as e:
        self.logger.warning(f"⚠️ Error clicking post button: {e}")
        return False
    
    async def reply_to_tweet(self, tweet_url, reply_content):
        """Tweet'e yanıt ver - OPTIMIZE EDİLDİ"""
        if not self.is_logged_in:
            if not await self.login():
                return False
        
        try:
            self.logger.info(f"💬 Replying to tweet...")
            
            await self.page.goto(tweet_url, wait_until="domcontentloaded", timeout=10000)
            await asyncio.sleep(2)
            
            # Reply butonuna tıkla
            try:
                reply_button = await self.page.wait_for_selector('div[data-testid="reply"]', timeout=5000)
                await reply_button.click()
                await asyncio.sleep(2)
            except Exception as e:
                self.logger.warning(f"⚠️ Could not find reply button: {e}")
                return False
            
            # Reply içeriğini yaz
            try:
                reply_text_area = await self.page.wait_for_selector('div[data-testid="tweetTextarea_0"]', timeout=5000)
                await reply_text_area.fill(reply_content)
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.warning(f"⚠️ Could not find reply text area: {e}")
                return False
            
            # Reply gönder
            try:
                post_button = await self.page.wait_for_selector('div[data-testid="tweetButton"]', timeout=3000)
                await post_button.click()
                await asyncio.sleep(2)
                self.logger.info("✅ Reply posted!")
                return True
            except Exception as e:
                self.logger.warning(f"⚠️ Could not find post button: {e}")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Error posting reply: {e}")
            return False
    
    async def get_user_recent_tweets(self, username, limit=3):
        """Kullanıcının son tweetlerini al - TIMEOUT FİXED"""
        if not self.is_logged_in:
            if not await self.login():
                return []

        try:
            self.logger.info(f"🔍 Getting recent tweets for @{username}")
        
        # Kullanıcı profiline git - timeout artırıldı
        await self.page.goto(f"https://twitter.com/{username}", 
                            wait_until="domcontentloaded", 
                            timeout=15000)  # 15 saniye
        await asyncio.sleep(3)  # Daha uzun bekleme
    
        tweets = []
        
        # Tweet'leri bul
        try:
            # Daha uzun timeout ile tweet'leri bekle
            await self.page.wait_for_selector('article[data-testid="tweet"]', timeout=8000)
            tweet_elements = await self.page.query_selector_all('article[data-testid="tweet"]')
            
            for i, tweet_element in enumerate(tweet_elements[:limit]):
                try:
                    # Tweet metnini al
                    text_element = await tweet_element.query_selector('div[data-testid="tweetText"]')
                    tweet_text = await text_element.inner_text() if text_element else "No text"
                    
                    # Tweet URL'ini al
                    link_element = await tweet_element.query_selector('a[href*="/status/"]')
                    tweet_url = await link_element.get_attribute("href") if link_element else None
                    if tweet_url and not tweet_url.startswith("https://"):
                        tweet_url = f"https://twitter.com{tweet_url}"
                    
                    # Son 4 saat içindeki tweetleri al (daha da genişletildi)
                    time_element = await tweet_element.query_selector('time')
                    if time_element:
                        datetime_attr = await time_element.get_attribute('datetime')
                        if datetime_attr:
                            tweet_time = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                            current_time = datetime.now(tweet_time.tzinfo)
                            
                            if current_time - tweet_time <= timedelta(hours=4):  # 4 saate çıkarıldı
                                tweet_data = {
                                    'text': tweet_text,
                                    'url': tweet_url,
                                    'username': username,
                                    'time': tweet_time
                                }
                                tweets.append(tweet_data)
                                self.logger.info(f"✅ Recent tweet found for @{username}: {tweet_text[:50]}...")
                
                except Exception as e:
                    self.logger.warning(f"⚠️ Error processing tweet {i+1}: {e}")
                    continue
            
            self.logger.info(f"📊 Found {len(tweets)} recent tweets for @{username}")
            return tweets
            
        except Exception as e:
            self.logger.warning(f"⚠️ Could not find tweets for @{username}: {e}")
            return []
    
        except Exception as e:
            self.logger.error(f"❌ Error getting recent tweets for @{username}: {e}")
            return []
    
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
