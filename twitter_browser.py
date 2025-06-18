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
                    '--memory-pressure-off',
                    '--max_old_space_size=4096',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                    '--disable-client-side-phishing-detection',
                    '--disable-default-apps',
                    '--disable-hang-monitor',
                    '--disable-popup-blocking',
                    '--disable-prompt-on-repost',
                    '--disable-sync',
                    '--disable-translate',
                    '--metrics-recording-only',
                    '--no-first-run',
                    '--safebrowsing-disable-auto-update',
                    '--enable-automation',
                    '--password-store=basic',
                    '--use-mock-keychain',
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
    
    async def recover_from_crash(self):
        """Recover from page crash"""
        try:
            self.logger.warning("🔄 Attempting to recover from page crash...")
            
            # Close current page if exists
            if self.page:
                try:
                    await self.page.close()
                except:
                    pass
            
            # Create new page
            self.page = await self.browser.new_page()
            
            # Re-apply anti-detection
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
            
            self.logger.info("✅ Page crash recovery successful")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Page crash recovery failed: {e}")
            return False
    
    async def quick_login_check(self):
        """HIZLI login durumu kontrolü"""
        try:
            self.logger.info("⚡ Quick login check...")
            
            # Home sayfasına git
            await self.page.goto("https://twitter.com/home", 
                               wait_until="domcontentloaded", 
                               timeout=10000)
            
            await asyncio.sleep(1)
            
            # Tweet butonu var mı kontrol et
            try:
                element = await self.page.wait_for_selector(
                    'a[data-testid="SideNav_NewTweet_Button"]', 
                    timeout=3000
                )
                if element:
                    self.logger.info("✅ Already logged in!")
                    self.is_logged_in = True
                    return True
            except:
                pass
            
            # URL kontrolü
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
    
    async def check_login_status(self):
        """Login durumunu kontrol et - quick_login_check'in alias'ı"""
        return await self.quick_login_check()
    
    async def direct_login(self):
        """DİREKT ve HIZLI login süreci"""
        try:
            self.logger.info("⚡ Starting DIRECT login...")
            self.login_attempts += 1
            self.last_login_attempt = time.time()
            
            # Login sayfasına git
            await self.page.goto("https://twitter.com/i/flow/login", 
                                wait_until="domcontentloaded", 
                                timeout=15000)
            
            await asyncio.sleep(2)
            
            # 1. USERNAME GİR
            username = os.environ.get('TWITTER_USERNAME') or os.environ.get('EMAIL_ADDRESS')
            self.logger.info(f"⚡ Entering username: {username}")
            
            # Username alanını bul ve doldur
            username_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[type="text"]'
            ]
            
            for selector in username_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.fill(selector, username)
                    self.logger.info("⚡ Username entered")
                    break
                except:
                    continue
            
            # Enter tuşuna bas (Next butonu yerine)
            await self.page.keyboard.press('Enter')
            self.logger.info("⚡ Enter pressed")
            await asyncio.sleep(2)
            
            # 2. USERNAME VERIFICATION (varsa)
            await self.handle_username_verification()
            
            # 3. PASSWORD GİR - GELİŞTİRİLMİŞ YAKLAŞIM
            password = os.environ.get('TWITTER_PASSWORD')
            self.logger.info("⚡ Looking for password field...")

            # Password alanını bekle - daha fazla selector ile
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[autocomplete="current-password"]',
                'input[data-testid="ocfPasswordInput"]',
                'input[placeholder*="password"]',
                'input[placeholder*="Password"]'
            ]

            password_found = False
            for selector in password_selectors:
                try:
                    self.logger.info(f"🔍 Trying password selector: {selector}")
                    password_element = await self.page.wait_for_selector(selector, timeout=5000)
                    
                    if password_element:
                        # Password alanını temizle ve doldur
                        await password_element.click()
                        await asyncio.sleep(1)
                        await password_element.fill('')  # Temizle
                        await password_element.fill(password)
                        self.logger.info("⚡ Password entered successfully")
                        
                        # Enter tuşuna bas
                        await self.page.keyboard.press('Enter')
                        self.logger.info("⚡ Enter pressed for login")
                        password_found = True
                        break
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ Password selector {selector} failed: {e}")
                    continue

            if not password_found:
                self.logger.error("❌ Could not find password field with any selector")
                return False
            
            # Login sonrası daha uzun bekleme ve debug
            await asyncio.sleep(5)

            # Sayfanın mevcut durumunu kontrol et
            try:
                current_url = self.page.url
                page_title = await self.page.title()
                self.logger.info(f"🔍 After login attempt - URL: {current_url}")
                self.logger.info(f"🔍 After login attempt - Title: {page_title}")
                
                # Hata mesajı var mı kontrol et
                error_selectors = [
                    'div[data-testid="error"]',
                    'div[role="alert"]',
                    'span[data-testid="error"]',
                    '.error',
                    '[data-testid="loginError"]'
                ]
                
                for error_selector in error_selectors:
                    try:
                        error_element = await self.page.wait_for_selector(error_selector, timeout=2000)
                        if error_element:
                            error_text = await error_element.inner_text()
                            self.logger.warning(f"⚠️ Login error detected: {error_text}")
                    except:
                        continue
                        
            except Exception as debug_error:
                self.logger.warning(f"⚠️ Debug info failed: {debug_error}")
            
            # Login sonrası kısa bekleme
            await asyncio.sleep(3)
            
            # 4. EMAIL VERIFICATION (varsa)
            await self.handle_email_verification()
            
            # 5. LOGIN KONTROLÜ
            if await self.quick_login_check():
                self.logger.info("🎉 DIRECT LOGIN SUCCESSFUL!")
                self.login_attempts = 0
                return True
            else:
                # Bir kez daha dene
                await asyncio.sleep(2)
                if await self.quick_login_check():
                    self.logger.info("🎉 DIRECT LOGIN SUCCESSFUL (retry)!")
                    self.login_attempts = 0
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
        """Email verification - EMAIL'DEN KOD AL"""
        try:
            self.logger.info("🔍 Checking for email verification...")
        
            # Email verification alanı var mı?
            verification_input = None
            try:
                verification_input = await self.page.wait_for_selector(
                    'input[data-testid="ocfEnterTextTextInput"]', 
                    timeout=3000
                )
            except:
                self.logger.info("ℹ️ No email verification needed")
                return True
        
            if not verification_input:
                return True
        
            self.logger.info("📧 Email verification required - getting code from email...")
        
            # Email'den doğrulama kodunu al (şifre otomatik kullanılacak)
            self.logger.info("📧 Retrieving verification code from email...")
            verification_code = self.email_handler.get_twitter_verification_code(timeout=90)
        
            if verification_code:
                self.logger.info(f"✅ Got verification code: {verification_code}")
            
                # Kodu gir
                await verification_input.fill(verification_code)
                await asyncio.sleep(1)
            
                # Enter tuşuna bas
                await self.page.keyboard.press('Enter')
                self.logger.info("✅ Verification code submitted")
            
                await asyncio.sleep(3)
                return True
            else:
                self.logger.error("❌ Could not get verification code from email")
                self.logger.info("⏳ Please enter verification code manually...")
                await asyncio.sleep(60)  # Manuel giriş için bekle
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
        """Tweet gönder - GELİŞTİRİLMİŞ"""
        if not self.is_logged_in:
            if not await self.login():
                return False
    
        # Check if page crashed
        try:
            await self.page.evaluate('1 + 1')
        except Exception as e:
            if "crashed" in str(e).lower():
                self.logger.warning("⚠️ Page crashed detected, attempting recovery...")
                if not await self.recover_from_crash():
                    return False
                # Re-login after recovery
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
            # Tweet compose alanını bul - GÜNCEL X.COM selectors
            compose_selectors = [
                # X.com yeni selectors
                'div[data-testid="tweetTextarea_0"]',
                'div[contenteditable="true"][data-testid="tweetTextarea_0"]',
                'div[role="textbox"][data-testid="tweetTextarea_0"]',
                # Genel selectors
                'div[contenteditable="true"][role="textbox"]',
                'div[contenteditable="true"]',
                'div[role="textbox"]',
                # Aria label ile
                'div[aria-label*="Post text"]',
                'div[aria-label*="Tweet text"]',
                'div[aria-label*="What is happening"]',
                'div[aria-label*="What\'s happening"]',
                # Placeholder ile
                'div[placeholder*="What is happening"]',
                'div[placeholder*="What\'s happening"]',
                # CSS class ile
                '.public-DraftEditor-content',
                '.notranslate.public-DraftEditor-content',
                'div[spellcheck="true"][role="textbox"]',
                'div[contenteditable="true"][spellcheck="true"]',
                # X.com specific
                'div[data-testid="tweetTextarea_0"][contenteditable="true"]',
                'div[data-contents="true"]',
                # Fallback selectors
                '[contenteditable="true"]',
                '[role="textbox"]'
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
                self.logger.warning("⚠️ Primary compose area not found, trying X.com specific methods...")
                
                # X.com özel metodu dene
                compose_element = await self.find_compose_area_x_com()
                
                if not compose_element:
                    self.logger.error("❌ Could not find tweet compose area with any method")
                    return False
        
            # Tweet içeriğini yaz
            await compose_element.click()
            await asyncio.sleep(1)
            await compose_element.fill(content)
            await asyncio.sleep(2)
        
            self.logger.info(f"📝 Tweet content entered: {content[:50]}...")

            # Debug: Sayfanın mevcut durumunu kontrol et
            try:
                current_url = self.page.url
                page_title = await self.page.title()
                self.logger.info(f"🔍 Debug - Current URL: {current_url}")
                self.logger.info(f"🔍 Debug - Page title: {page_title}")
                
                # Sayfada bulunan tüm button'ları listele
                all_buttons = await self.page.query_selector_all('button, div[role="button"]')
                self.logger.info(f"🔍 Debug - Found {len(all_buttons)} buttons on page")
                
            except Exception as debug_error:
                self.logger.warning(f"⚠️ Debug info failed: {debug_error}")
        
            # Tweet gönder butonunu bul
            post_selectors = [
                'div[data-testid="tweetButton"]',
                'div[data-testid="tweetButtonInline"]',
                'button[data-testid="tweetButton"]',
                'button[data-testid="tweetButtonInline"]',
                '[role="button"][data-testid="tweetButton"]',
                'div[role="button"][data-testid="tweetButton"]',
                'button[role="button"][data-testid="tweetButton"]',
                'div[aria-label*="Post"]',
                'button[aria-label*="Post"]',
                'div[aria-label*="Tweet"]',
                'button[aria-label*="Tweet"]',
                'button[type="submit"]',
                'div[role="button"]:has-text("Post")',
                'button:has-text("Post")',
                'div[role="button"]:has-text("Tweet")',
                'button:has-text("Tweet")'
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
    
    async def find_compose_area_x_com(self):
        """X.com için özel compose area bulma metodu"""
        try:
            self.logger.info("🔍 Looking for X.com compose area...")
            
            # X.com'da compose area'yı açmak için farklı yöntemler dene
            methods = [
                # Method 1: Direct compose area
                {
                    'name': 'Direct compose area',
                    'action': lambda: None,
                    'selectors': [
                        'div[data-testid="tweetTextarea_0"]',
                        'div[contenteditable="true"][role="textbox"]',
                        'div[aria-label*="Post text"]'
                    ]
                },
                # Method 2: Click compose button first
                {
                    'name': 'Click compose button',
                    'action': self.click_compose_button,
                    'selectors': [
                        'div[data-testid="tweetTextarea_0"]',
                        'div[contenteditable="true"]'
                    ]
                },
                # Method 3: Use keyboard shortcut
                {
                    'name': 'Keyboard shortcut',
                    'action': self.use_compose_shortcut,
                    'selectors': [
                        'div[data-testid="tweetTextarea_0"]',
                        'div[contenteditable="true"]'
                    ]
                }
            ]
            
            for method in methods:
                try:
                    self.logger.info(f"🔄 Trying method: {method['name']}")
                    
                    # Execute method action
                    if method['action']:
                        await method['action']()
                        await asyncio.sleep(2)
                    
                    # Try to find compose area
                    for selector in method['selectors']:
                        try:
                            element = await self.page.wait_for_selector(selector, timeout=3000)
                            if element:
                                # Test if element is actually editable
                                is_editable = await element.evaluate('el => el.contentEditable === "true" || el.tagName === "TEXTAREA" || el.tagName === "INPUT"')
                                if is_editable:
                                    self.logger.info(f"✅ Found working compose area: {selector}")
                                    return element
                        except:
                            continue
                            
                except Exception as e:
                    self.logger.warning(f"⚠️ Method {method['name']} failed: {e}")
                    continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error in find_compose_area_x_com: {e}")
            return None

    async def click_compose_button(self):
        """Compose butonuna tıkla"""
        try:
            compose_buttons = [
                'a[data-testid="SideNav_NewTweet_Button"]',
                'button[data-testid="SideNav_NewTweet_Button"]',
                'a[href="/compose/tweet"]',
                'a[href="/compose/post"]',
                'button[aria-label*="Post"]',
                'button[aria-label*="Tweet"]',
                'div[data-testid="SideNav_NewTweet_Button"]'
            ]
            
            for selector in compose_buttons:
                try:
                    button = await self.page.wait_for_selector(selector, timeout=2000)
                    if button:
                        await button.click()
                        self.logger.info(f"✅ Clicked compose button: {selector}")
                        return True
                except:
                    continue
                
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error clicking compose button: {e}")
            return False

    async def use_compose_shortcut(self):
        """Compose kısayolunu kullan"""
        try:
            # X.com'da 'n' tuşu compose açar
            await self.page.keyboard.press('n')
            self.logger.info("⌨️ Used keyboard shortcut 'n'")
            return True
        except Exception as e:
            self.logger.warning(f"⚠️ Error using compose shortcut: {e}")
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
            reply_button_selector = 'div[data-testid="reply"]'
            try:
                reply_button = await self.page.wait_for_selector(reply_button_selector, timeout=5000)
                await reply_button.click()
            except Exception as e:
                self.logger.warning(f"⚠️ Could not find reply button: {e}")
                return False
            
            await asyncio.sleep(2)
            
            # Reply içeriğini yaz
            reply_text_area_selector = 'div[data-testid="tweetTextarea_0"]'
            try:
                reply_text_area = await self.page.wait_for_selector(reply_text_area_selector, timeout=5000)
                await reply_text_area.fill(reply_content)
            except Exception as e:
                self.logger.warning(f"⚠️ Could not find reply text area: {e}")
                return False
            
            await asyncio.sleep(1)
            
            # Reply gönder
            post_button_selector = 'div[data-testid="tweetButton"]'
            try:
                post_button = await self.page.wait_for_selector(post_button_selector, timeout=5000)
                await post_button.click()
            except Exception as e:
                self.logger.warning(f"⚠️ Could not find post button: {e}, trying keyboard shortcut")
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
        """Kullanıcının son tweet'ini al - BASİTLEŞTİRİLMİŞ"""
        if not self.is_logged_in:
            if not await self.login():
                return None

        # Check if page crashed
        try:
            await self.page.evaluate('1 + 1')
        except Exception as e:
            if "crashed" in str(e).lower():
                self.logger.warning("⚠️ Page crashed detected, attempting recovery...")
                if not await self.recover_from_crash():
                    return None
                # Re-login after recovery
                if not await self.login():
                    return None

        try:
            self.logger.info(f"🔍 Getting latest tweet for @{username}")
        
            # Kullanıcı profiline git
            await self.page.goto(f"https://twitter.com/{username}", 
                                wait_until="domcontentloaded", 
                                timeout=15000)
            await asyncio.sleep(3)
        
            # İlk tweet'i bul
            try:
                first_tweet = await self.page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)
                
                if first_tweet:
                    # Tweet metnini al
                    try:
                        text_element = await first_tweet.query_selector('div[data-testid="tweetText"]')
                        tweet_text = await text_element.inner_text() if text_element else "No text"
                    except:
                        tweet_text = "No text"
                    
                    # Tweet URL'ini al
                    try:
                        link_element = await first_tweet.query_selector('a[href*="/status/"]')
                        tweet_url = await link_element.get_attribute("href") if link_element else None
                        if tweet_url and not tweet_url.startswith("https://"):
                            tweet_url = f"https://twitter.com{tweet_url}"
                    except:
                        tweet_url = None
                
                    tweet_data = {
                        'text': tweet_text,
                        'url': tweet_url,
                        'username': username
                    }
                    
                    self.logger.info(f"✅ Tweet found for @{username}: {tweet_text[:50]}...")
                    return tweet_data
                
            except Exception as e:
                self.logger.warning(f"⚠️ Could not find tweet for @{username}: {e}")
                return None
        
        except Exception as e:
            self.logger.error(f"❌ Error getting tweet for @{username}: {e}")
            return None
    
    async def get_user_recent_tweets(self, username, limit=3):
        """Kullanıcının son tweetlerini al"""
        if not self.is_logged_in:
            if not await self.login():
                return []

        # Check if page crashed
        try:
            await self.page.evaluate('1 + 1')
        except Exception as e:
            if "crashed" in str(e).lower():
                self.logger.warning("⚠️ Page crashed detected, attempting recovery...")
                if not await self.recover_from_crash():
                    return []
                # Re-login after recovery
                if not await self.login():
                    return []

        try:
            self.logger.info(f"🔍 Getting recent tweets for @{username}")
        
            # Kullanıcı profiline git
            await self.page.goto(f"https://twitter.com/{username}", 
                                wait_until="domcontentloaded", 
                                timeout=15000)
            await asyncio.sleep(3)
        
            tweets = []
            
            # Tweet'leri bul
            try:
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
                        
                        # Tweet zamanını kontrol et (son 1 saat içinde mi?)
                        time_element = await tweet_element.query_selector('time')
                        if time_element:
                            datetime_attr = await time_element.get_attribute('datetime')
                            if datetime_attr:
                                from datetime import datetime, timedelta
                                tweet_time = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                                current_time = datetime.now(tweet_time.tzinfo)
                                
                                # Son 1 saat içindeki tweetleri al
                                if current_time - tweet_time <= timedelta(hours=1):
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
    
    async def post_tweet_thread(self, content_parts):
        """Tweet thread gönder - + butonu ile"""
        if not self.is_logged_in:
            if not await self.login():
                return False

        try:
            self.logger.info(f"📝 Posting tweet thread with {len(content_parts)} parts...")
        
            # Home sayfasına git
            await self.page.goto("https://twitter.com/home", 
                                wait_until="domcontentloaded", 
                                timeout=15000)
            await asyncio.sleep(3)
        
            # İlk tweet'i gönder
            first_tweet = content_parts[0]
        
            # Tweet compose alanını bul
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
                        break
                except:
                    continue
        
            if not compose_element:
                self.logger.error("❌ Could not find tweet compose area")
                return False
        
            # İlk tweet'i yaz
            await compose_element.click()
            await asyncio.sleep(1)
            await compose_element.fill(first_tweet)
            await asyncio.sleep(2)
            
            # Diğer tweet'leri ekle
            for i, tweet_part in enumerate(content_parts[1:], 1):
                try:
                    self.logger.info(f"➕ Adding tweet part {i+1}/{len(content_parts)}...")
                    
                    # + (Ekle) butonunu bul ve tıkla
                    add_button_selectors = [
                        'button[aria-label*="Add"]',
                        'button[aria-label*="Ekle"]',
                        'div[aria-label*="Add"]',
                        'div[aria-label*="Ekle"]',
                        'button[data-testid="addButton"]',
                        'div[data-testid="addButton"]',
                        'button:has-text("+")',
                        'div:has-text("+")'
                    ]
                    
                    add_button = None
                    for selector in add_button_selectors:
                        try:
                            add_button = await self.page.wait_for_selector(selector, timeout=3000)
                            if add_button:
                                await add_button.click()
                                await asyncio.sleep(2)
                                break
                        except:
                            continue
                
                    if not add_button:
                        self.logger.warning(f"⚠️ Could not find add button for tweet {i+1}")
                        continue
                    
                    # Yeni tweet alanını bul ve doldur
                    new_tweet_selectors = [
                        f'div[data-testid="tweetTextarea_{i}"]',
                        'div[contenteditable="true"]:last-of-type',
                        'div[role="textbox"]:last-of-type'
                    ]
                    
                    new_compose_element = None
                    for selector in new_tweet_selectors:
                        try:
                            new_compose_element = await self.page.wait_for_selector(selector, timeout=3000)
                            if new_compose_element:
                                break
                        except:
                            continue
                
                    if new_compose_element:
                        await new_compose_element.click()
                        await asyncio.sleep(1)
                        await new_compose_element.fill(tweet_part)
                        await asyncio.sleep(1)
                        self.logger.info(f"✅ Tweet part {i+1} added")
                    else:
                        self.logger.warning(f"⚠️ Could not find compose area for tweet {i+1}")
                
                except Exception as e:
                    self.logger.error(f"❌ Error adding tweet part {i+1}: {e}")
                    continue
            
            # Thread'i gönder
            post_selectors = [
                'div[data-testid="tweetButton"]',
                'button[data-testid="tweetButton"]',
                'div[role="button"][data-testid="tweetButton"]'
            ]
        
            post_button = None
            for selector in post_selectors:
                try:
                    post_button = await self.page.wait_for_selector(selector, timeout=3000)
                    if post_button:
                        is_disabled = await post_button.get_attribute('aria-disabled')
                        if is_disabled != 'true':
                            break
                except:
                    continue
        
            if post_button:
                await post_button.click()
                await asyncio.sleep(3)
                self.logger.info("✅ Tweet thread posted successfully!")
                return True
            else:
                self.logger.error("❌ Could not find active post button")
                return False
        
        except Exception as e:
            self.logger.error(f"❌ Error posting tweet thread: {e}")
            return False
    
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
