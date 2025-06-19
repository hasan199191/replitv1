from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import asyncio
import time
import os
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List
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
    
    def smart_split_content(self, content: str, max_length: int = 270) -> List[str]:
        """İçeriği akıllı şekilde tweet'lere böl"""
        if not content:
            return []
        
        # Eğer tek tweet'e sığıyorsa direkt döndür
        if len(content) <= max_length:
            return [content]
        
        tweets = []
        
        # Önce paragrafları ayır
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if not paragraphs:
            paragraphs = [content]
        
        current_tweet = ""
        tweet_number = 1
        
        for paragraph in paragraphs:
            # Paragraf çok uzunsa cümlelere böl
            if len(paragraph) > max_length:
                sentences = [s.strip() + '.' for s in paragraph.split('.') if s.strip()]
                
                for sentence in sentences:
                    # Thread numarası için yer ayır
                    thread_prefix = f"{tweet_number}/X "
                    available_space = max_length - len(thread_prefix) - 10  # Buffer
                    
                    # Cümle tek başına çok uzunsa zorla böl
                    if len(sentence) > available_space:
                        words = sentence.split()
                        temp_sentence = ""
                        
                        for word in words:
                            if len(temp_sentence + " " + word) <= available_space:
                                temp_sentence += (" " + word if temp_sentence else word)
                            else:
                                if temp_sentence:
                                    tweets.append(temp_sentence)
                                    tweet_number += 1
                                temp_sentence = word
                        
                        if temp_sentence:
                            tweets.append(temp_sentence)
                            tweet_number += 1
                    else:
                        # Normal cümle ekleme
                        if len(current_tweet + " " + sentence) <= available_space:
                            current_tweet += (" " + sentence if current_tweet else sentence)
                        else:
                            if current_tweet:
                                tweets.append(current_tweet)
                                tweet_number += 1
                            current_tweet = sentence
            else:
                # Paragraf normal uzunlukta
                thread_prefix = f"{tweet_number}/X "
                available_space = max_length - len(thread_prefix) - 10
                
                if len(current_tweet + " " + paragraph) <= available_space:
                    current_tweet += (" " + paragraph if current_tweet else paragraph)
                else:
                    if current_tweet:
                        tweets.append(current_tweet)
                        tweet_number += 1
                    current_tweet = paragraph
        
        # Son tweet'i ekle
        if current_tweet:
            tweets.append(current_tweet)
        
        # Thread numaralarını ekle
        total_tweets = len(tweets)
        if total_tweets > 1:
            for i in range(total_tweets):
                tweets[i] = f"{i+1}/{total_tweets} {tweets[i]}"
                
                # Final karakter kontrolü
                if len(tweets[i]) > max_length:
                    tweets[i] = tweets[i][:max_length-3] + "..."
        
        return tweets
    
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
                    '--start-maximized'
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
        """DÜZELTME: DOĞRU login durumu kontrolü"""
        try:
            self.logger.info("⚡ Quick login check...")
            
            # Home sayfasına git
            await self.page.goto("https://x.com/home", 
                               wait_until="domcontentloaded", 
                               timeout=15000)
            
            await asyncio.sleep(3)
            
            # URL kontrolü - DÜZELTME: Login sayfasında mıyız?
            current_url = self.page.url
            self.logger.info(f"📍 Current URL: {current_url}")
            
            # Login sayfasındaysak, login olmamışız
            if "login" in current_url or "flow" in current_url:
                self.logger.info("❌ Redirected to login page - not logged in")
                self.is_logged_in = False
                return False
            
            # Home sayfasındaysak ve login sayfası değilse
            if "/home" in current_url and "login" not in current_url:
                # Tweet butonu var mı kontrol et
                try:
                    element = await self.page.wait_for_selector(
                        'a[data-testid="SideNav_NewTweet_Button"]', 
                        timeout=5000
                    )
                    if element:
                        self.logger.info("✅ Already logged in - tweet button found!")
                        self.is_logged_in = True
                        return True
                except:
                    pass
                
                # Tweet butonu yoksa da URL'e göre login olmuş sayalım
                self.logger.info("✅ Login confirmed by URL (no login redirect)!")
                self.is_logged_in = True
                return True
            
            self.logger.info("❌ Not logged in")
            self.is_logged_in = False
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️ Quick check failed: {e}")
            self.is_logged_in = False
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
            self.logger.info("⚡ Enter pressed")
            await asyncio.sleep(3)
            
            # 2. USERNAME VERIFICATION (varsa)
            await self.handle_username_verification()
            
            # 3. PASSWORD GİR - DİREKT YAKLAŞIM
            password = os.environ.get('TWITTER_PASSWORD')
            self.logger.info("⚡ Looking for password field...")
            
            # Password alanını bekle ve direkt doldur
            try:
                # Kısa timeout ile password alanını bekle
                await self.page.wait_for_selector('input[type="password"]', timeout=10000)
                
                # Direkt password'u yaz (click yapmadan)
                await self.page.fill('input[type="password"]', password)
                self.logger.info("⚡ Password entered directly")
                
                # Hemen Enter tuşuna bas
                await self.page.keyboard.press('Enter')
                self.logger.info("⚡ Enter pressed for login")
                
            except Exception as e:
                self.logger.error(f"❌ Password field error: {e}")
                return False
            
            # Login sonrası bekleme
            await asyncio.sleep(5)
            
            # 4. EMAIL VERIFICATION (varsa)
            await self.handle_email_verification()
            
            # 5. LOGIN KONTROLÜ - DÜZELTME
            self.logger.info("🔍 Checking login success...")
            
            # Birkaç kez dene
            for attempt in range(3):
                if await self.quick_login_check():
                    self.logger.info("🎉 DIRECT LOGIN SUCCESSFUL!")
                    self.login_attempts = 0
                    return True
                else:
                    self.logger.warning(f"⚠️ Login check failed, attempt {attempt + 1}/3")
                    await asyncio.sleep(3)
            
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
                    await asyncio.sleep(3)
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
                    timeout=5000
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
            
                await asyncio.sleep(5)
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
    
    async def post_thread(self, content):
        """THREAD OLARAK tweet gönder - LOGIN KONTROLÜ DÜZELTİLDİ"""
        try:
            # MUTLAKA login kontrolü yap
            self.logger.info("🔍 Checking login status before posting...")
            if not await self.quick_login_check():
                self.logger.warning("❌ Not logged in, attempting login...")
                if not await self.login():
                    self.logger.error("❌ Login failed, cannot post thread")
                    return False
        
            # İçeriği işle
            if isinstance(content, str):
                tweets = self.smart_split_content(content, max_length=270)
            elif isinstance(content, list):
                tweets = []
                for item in content:
                    if isinstance(item, str):
                        if len(item) > 270:
                            split_tweets = self.smart_split_content(item, max_length=270)
                            tweets.extend(split_tweets)
                        else:
                            tweets.append(item)
                else:
                    tweets.append(str(item))
        else:
            tweets = [str(content)]
    
        if not tweets:
            self.logger.error("❌ No valid tweets to send")
            return False
    
        self.logger.info(f"🧵 Sending thread with {len(tweets)} tweets")
    
        # Home sayfasına git - TEKRAR LOGIN KONTROLÜ
        self.logger.info("🏠 Going to home page...")
        await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        
        # URL kontrolü - login sayfasına yönlendirildik mi?
        current_url = self.page.url
        self.logger.info(f"📍 Current URL after home navigation: {current_url}")
        
        if "login" in current_url or "flow" in current_url:
            self.logger.error("❌ Redirected to login page! Attempting re-login...")
            if not await self.login():
                self.logger.error("❌ Re-login failed")
                return False
            
            # Login sonrası tekrar home'a git
            await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            # Tekrar kontrol et
            current_url = self.page.url
            if "login" in current_url or "flow" in current_url:
                self.logger.error("❌ Still on login page after re-login attempt")
                return False
    
        try:
            # İçeriği işle
            if isinstance(content, str):
                tweets = self.smart_split_content(content, max_length=270)
            elif isinstance(content, list):
                tweets = []
                for item in content:
                    if isinstance(item, str):
                        if len(item) > 270:
                            split_tweets = self.smart_split_content(item, max_length=270)
                            tweets.extend(split_tweets)
                        else:
                            tweets.append(item)
                    else:
                        tweets.append(str(item))
            else:
                tweets = [str(content)]
        
            if not tweets:
                self.logger.error("❌ No valid tweets to send")
                return False
        
            self.logger.info(f"🧵 Sending thread with {len(tweets)} tweets")
        
            # Home sayfasına git ve orada kal
            self.logger.info("🏠 Going to home page...")
            await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)
        
            # Debug: Analyze page elements if we can't find tweet button
            self.logger.info("🔍 Analyzing page for tweet buttons...")
            await self.debug_page_elements()
            
            # Tweet butonu selectors - güncel Twitter arayüzü için
            tweet_button_selectors = [
                # Yeni X.com selectors
                'a[data-testid="SideNav_NewTweet_Button"]',  # Sidebar tweet button
                'div[data-testid="SideNav_NewTweet_Button"]',  # Alternative
                'button[data-testid="SideNav_NewTweet_Button"]',  # Button version
                
                # Post button variations
                'a[aria-label="Post"]',  # Post button
                'button[aria-label="Post"]',  # Post button alternative
                'div[aria-label="Post"]',  # Div version
                
                # Compose variations
                'a[href="/compose/tweet"]',  # Compose link
                'a[href="/compose/post"]',  # New compose link
                
                # Generic tweet buttons
                '[data-testid="tweetButtonInline"]',  # Inline tweet button
                '[data-testid="tweetButton"]',  # Generic tweet button
                
                # Fallback selectors
                'a[role="button"][aria-label*="Tweet"]',
                'button[role="button"][aria-label*="Tweet"]',
                'a[role="button"][aria-label*="Post"]',
                'button[role="button"][aria-label*="Post"]'
            ]
        
            tweet_button = None
            for selector in tweet_button_selectors:
                try:
                    self.logger.info(f"🔍 Looking for tweet button: {selector}")
                    tweet_button = await self.page.wait_for_selector(selector, timeout=5000)
                    if tweet_button:
                        is_visible = await tweet_button.is_visible()
                        if is_visible:
                            self.logger.info(f"✅ Found tweet button: {selector}")
                            break
                        else:
                            tweet_button = None
                except Exception as e:
                    self.logger.warning(f"⚠️ Selector {selector} failed: {e}")
                    continue
        
            if not tweet_button:
                self.logger.error("❌ Could not find tweet button")
                return False
        
            # Tweet butonuna tıkla
            await tweet_button.click()
            await asyncio.sleep(3)
        
            # Tweet yazma alanını bul - güncel selectors
            compose_selectors = [
                'div[data-testid="tweetTextarea_0"]',  # Ana textarea
                'div[contenteditable="true"][aria-label*="What"]',  # What's happening
                'div[contenteditable="true"][data-testid*="tweet"]',  # Tweet içeren
                'div[contenteditable="true"][role="textbox"]',  # Textbox role
                'div[contenteditable="true"]'  # Genel contenteditable
            ]
        
            compose_area = None
            for selector in compose_selectors:
                try:
                    self.logger.info(f"🔍 Looking for compose area: {selector}")
                    compose_area = await self.page.wait_for_selector(selector, timeout=10000)
                    if compose_area:
                        is_visible = await compose_area.is_visible()
                        if is_visible:
                            self.logger.info(f"✅ Found compose area: {selector}")
                            break
                        else:
                            compose_area = None
                except Exception as e:
                    self.logger.warning(f"⚠️ Compose selector {selector} failed: {e}")
                    continue
        
            if not compose_area:
                self.logger.error("❌ Could not find compose area")
                return False
        
            # İlk tweet'i yaz
            await compose_area.click()
            await asyncio.sleep(1)
            await compose_area.fill(tweets[0])
            self.logger.info(f"✅ First tweet written: {tweets[0][:50]}...")
            await asyncio.sleep(2)
        
            # Eğer birden fazla tweet varsa thread oluştur
            if len(tweets) > 1:
                for i, tweet_text in enumerate(tweets[1:], start=2):
                    self.logger.info(f"➕ Adding tweet {i}/{len(tweets)}")
                
                    # Thread butonunu bul ve tıkla
                    thread_button_selectors = [
                        'div[aria-label="Add another post"]',
                        'div[aria-label="Add another Tweet"]',
                        'button[aria-label="Add post"]',
                        'div[data-testid="addButton"]'
                    ]
                
                    thread_button = None
                    for selector in thread_button_selectors:
                        try:
                            thread_button = await self.page.wait_for_selector(selector, timeout=5000)
                            if thread_button:
                                break
                        except Exception as e:
                            self.logger.warning(f"⚠️ Thread button selector {selector} failed: {e}")
                            continue
                
                    if not thread_button:
                        self.logger.warning(f"⚠️ Could not find thread button, posting single tweet")
                        break
                
                    await thread_button.click()
                    await asyncio.sleep(3)
                
                    # Yeni tweet alanını bul
                    new_compose_selectors = [
                        f'div[data-testid="tweetTextarea_{i-1}"]',
                        'div[contenteditable="true"]:last-of-type'
                    ]
                
                    new_compose_area = None
                    for selector in new_compose_selectors:
                        try:
                            new_compose_area = await self.page.wait_for_selector(selector, timeout=5000)
                            if new_compose_area:
                                break
                        except Exception as e:
                            self.logger.warning(f"⚠️ New compose selector {selector} failed: {e}")
                            continue
                
                    if not new_compose_area:
                        # Tüm compose alanlarını bul ve sonuncusunu kullan
                        all_areas = await self.page.query_selector_all('div[contenteditable="true"]')
                        if all_areas and len(all_areas) >= i:
                            new_compose_area = all_areas[-1]
                
                    if new_compose_area:
                        await new_compose_area.click()
                        await asyncio.sleep(1)
                        await new_compose_area.fill(tweet_text)
                        self.logger.info(f"✅ Tweet {i} written: {tweet_text[:50]}...")
                        await asyncio.sleep(2)
                    else:
                        self.logger.error(f"❌ Could not find compose area for tweet {i}")
                        break
        
            # Tweet/Thread'i gönder
            post_button_selectors = [
                'div[data-testid="tweetButton"]',
                'button[data-testid="tweetButton"]',
                'div[data-testid="tweetButtonInline"]',
                'button[role="button"][aria-label*="Post"]'
            ]
        
            post_button = None
            for selector in post_button_selectors:
                try:
                    post_button = await self.page.wait_for_selector(selector, timeout=5000)
                    if post_button:
                        is_enabled = await post_button.is_enabled()
                        if is_enabled:
                            self.logger.info(f"✅ Found enabled post button: {selector}")
                            break
                        else:
                            post_button = None
                except Exception as e:
                    self.logger.warning(f"⚠️ Post button selector {selector} failed: {e}")
                    continue
        
            if not post_button:
                self.logger.error("❌ Could not find enabled post button")
                return False
        
            # Gönder
            await post_button.click()
            await asyncio.sleep(5)
        
            self.logger.info("🎉 THREAD SUCCESSFULLY POSTED!")
            return True
        
        except Exception as e:
            self.logger.error(f"❌ Thread posting error: {e}")
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
        if not await self.quick_login_check():
            if not await self.login():
                return None

        try:
            self.logger.info(f"🔍 Getting latest tweet for @{username}")
        
            # Kullanıcı profiline git
            profile_url = f"https://x.com/{username}"
            await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)
        
            # Sayfanın yüklendiğini kontrol et
            current_url = self.page.url
            if "login" in current_url or "flow" in current_url:
                self.logger.error(f"❌ Redirected to login when accessing @{username}")
                return None
        
            # Tweet'leri bul - daha kapsamlı selectors
            tweet_selectors = [
                'article[data-testid="tweet"]',
                'div[data-testid="cellInnerDiv"] article',
                'article[role="article"]',
                '[data-testid="tweet"]',
                'div[data-testid="tweet"]'
            ]
        
            first_tweet = None
            for selector in tweet_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    tweets = await self.page.query_selector_all(selector)
                    if tweets:
                        # İlk tweet'i al (en üstteki)
                        first_tweet = tweets[0]
                        self.logger.info(f"✅ Found {len(tweets)} tweets with selector: {selector}")
                        break
                except Exception as e:
                    self.logger.warning(f"⚠️ Tweet selector {selector} failed: {e}")
                    continue
        
            if not first_tweet:
                self.logger.warning(f"⚠️ No tweets found for @{username}")
                return None
        
            # Tweet bilgilerini al
            tweet_data = {'username': username}
        
            # Tweet metni - daha güvenilir extraction
            try:
                text_selectors = [
                    'div[data-testid="tweetText"]',
                    'div[lang] span',
                    'span[lang]',
                    'div[dir="auto"] span'
                ]
            
                tweet_text = ""
                for selector in text_selectors:
                    try:
                        text_elements = await first_tweet.query_selector_all(selector)
                        if text_elements:
                            text_parts = []
                            for elem in text_elements:
                                text = await elem.inner_text()
                                if text and text.strip():
                                    text_parts.append(text.strip())
                            if text_parts:
                                tweet_text = " ".join(text_parts)
                                break
                    except Exception as e:
                        self.logger.warning(f"⚠️ Text selector {selector} failed: {e}")
                        continue
            
                tweet_data['text'] = tweet_text if tweet_text else "No text found"
            
            except Exception as e:
                self.logger.warning(f"⚠️ Could not get tweet text: {e}")
                tweet_data['text'] = "No text found"
        
            # Tweet zamanı
            try:
                time_element = await first_tweet.query_selector('time')
                if time_element:
                    tweet_time = await time_element.get_attribute("datetime")
                    tweet_data['time'] = tweet_time
                else:
                    tweet_data['time'] = None
            except Exception as e:
                self.logger.warning(f"⚠️ Could not get tweet time: {e}")
                tweet_data['time'] = None
        
            # Tweet URL'i
            try:
                link_element = await first_tweet.query_selector('a[href*="/status/"]')
                if link_element:
                    href = await link_element.get_attribute("href")
                    if href:
                        if not href.startswith("https://"):
                            href = f"https://x.com{href}"
                        tweet_data['url'] = href
                    else:
                        tweet_data['url'] = None
                else:
                    tweet_data['url'] = None
            except Exception as e:
                self.logger.warning(f"⚠️ Could not get tweet URL: {e}")
                tweet_data['url'] = None
        
            self.logger.info(f"✅ Tweet data retrieved for @{username}")
            self.logger.info(f"📝 Text: {tweet_data['text'][:100]}...")
        
            return tweet_data
        
        except Exception as e:
            self.logger.error(f"❌ Error getting tweet for @{username}: {e}")
            return None
    
    async def get_latest_tweet_id(self, username):
        """Bir kullanıcının son tweet ID'sini al - GELİŞTİRİLMİŞ"""
        if not username:
            self.logger.error("❌ Invalid username provided")
            return None
            
        try:
            # Clean username
            username = username.strip().replace("@", "")
            
            # Profile sayfasına git (Retry logic ekle)
            retries = 3
            for attempt in range(retries):
                try:
                    await self.page.goto(f"https://x.com/{username}", wait_until="domcontentloaded", timeout=40000)
                    await asyncio.sleep(3)
                    break
                except Exception as e:
                    self.logger.warning(f"⚠️ Profile page navigation failed (Attempt {attempt + 1}/{retries}): {e}")
                    if attempt == retries - 1:
                        self.logger.error("❌ Profile page navigation failed after retries")
                        return None

            # Tweet elementlerini bulmak için birden fazla selector dene
            tweet_selectors = [
                'article[data-testid="tweet"]',
                '[data-testid="tweet"]',
                'div[data-testid="cellInnerDiv"]',
                'article[role="article"]'
            ]

            for selector in tweet_selectors:
                try:
                    tweets = await self.page.query_selector_all(selector)
                    if tweets and len(tweets) > 0:
                        self.logger.info(f"✅ Found {len(tweets)} tweets with selector: {selector}")
                        
                        # Birden fazla yöntemle tweet ID'sini almayı dene
                        for tweet in tweets:
                            try:
                                # 1. Link yöntemi
                                link = await tweet.query_selector('a[href*="/status/"]')
                                if link:
                                    href = await link.get_attribute('href')
                                    if href and '/status/' in href:
                                        tweet_id = href.split('/status/')[1].split('/')[0]
                                        if tweet_id.isalnum():
                                            self.logger.info(f"✅ Found tweet ID via link: {tweet_id}")
                                            return tweet_id
                                
                                # 2. Data attribute yöntemi
                                data_tweet_id = await tweet.get_attribute('data-tweet-id')
                                if data_tweet_id and data_tweet_id.isalnum():
                                    self.logger.info(f"✅ Found tweet ID via data attribute: {data_tweet_id}")
                                    return data_tweet_id
                                    
                                # 3. Article ID yöntemi
                                article_id = await tweet.get_attribute('id')
                                if article_id and 'tweet-' in article_id:
                                    tweet_id = article_id.split('tweet-')[1]
                                    if tweet_id.isalnum():
                                        self.logger.info(f"✅ Found tweet ID via article ID: {tweet_id}")
                                        return tweet_id
                                        
                            except Exception as e:
                                self.logger.warning(f"⚠️ Error extracting ID from tweet element: {e}")
                                continue
                                
                except Exception as e:
                    self.logger.warning(f"⚠️ Error with selector {selector}: {e}")
                    continue

            self.logger.error(f"❌ Could not find any tweet IDs for @{username}")
            return None

        except Exception as e:
            self.logger.error(f"❌ Error getting latest tweet ID for @{username}: {e}")
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
    
    async def reply_to_latest_tweet(self, username, reply_content):
        """Bir kullanıcının son tweetine yanıt ver"""
        if not self.is_logged_in:
            self.logger.info("🔍 Checking login status for reply...")
            if not await self.quick_login_check():
                if not await self.login():
                    return False

        try:
            self.logger.info(f"💬 Fetching latest tweet for @{username}...")

            # Son tweet ID'sini al
            tweet_id = await self.get_latest_tweet_id(username)
            if not tweet_id:
                self.logger.error(f"❌ Could not fetch latest tweet ID for @{username}")
                return False

            # Tweet URL'sini oluştur
            tweet_url = f"https://x.com/{username}/status/{tweet_id}"
            self.logger.info(f"💬 Replying to tweet: {tweet_url}")

            # Tweet sayfasına git
            await self.page.goto(tweet_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Reply butonuna tıkla
            try:
                reply_button = await self.page.wait_for_selector('div[data-testid="reply"]', timeout=10000)
                if reply_button:
                    await reply_button.click()
                    await asyncio.sleep(2)
                else:
                    self.logger.error("❌ Reply button not found!")
                    return False
            except Exception as e:
                self.logger.error(f"⚠️ Error clicking reply button: {e}")
                return False

            # Reply içeriğini yaz
            try:
                reply_area = await self.page.wait_for_selector('div[data-testid="tweetTextarea_0"]', timeout=10000)
                if reply_area:
                    await reply_area.fill(reply_content)
                    await asyncio.sleep(2)
                else:
                    self.logger.error("❌ Reply area not found!")
                    return False
            except Exception as e:
                self.logger.error(f"⚠️ Error filling reply content: {e}")
                return False

            # Reply gönder
            try:
                send_button = await self.page.wait_for_selector('div[data-testid="tweetButton"]', timeout=10000)
                if send_button:
                    await send_button.click()
                    await asyncio.sleep(5)
                    self.logger.info("✅ Reply posted!")
                    return True
                else:
                    self.logger.error("❌ Send button not found!")
                    return False
            except Exception as e:
                self.logger.error(f"⚠️ Error clicking send button: {e}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error replying to latest tweet for @{username}: {e}")
            return False
    
    async def debug_page_elements(self):
        """Debug: Sayfadaki elementleri analiz et"""
        try:
            self.logger.info("🔍 DEBUG: Analyzing page elements...")
        
            # Sayfa URL'i
            current_url = self.page.url
            self.logger.info(f"📍 Current URL: {current_url}")
        
            # Sayfa başlığı
            title = await self.page.title()
            self.logger.info(f"📄 Page title: {title}")
        
            # Tüm data-testid elementler
            testid_elements = await self.page.query_selector_all('[data-testid]')
            self.logger.info(f"🏷️ Found {len(testid_elements)} elements with data-testid")
        
            tweet_related_testids = []
            for elem in testid_elements:
                try:
                    testid = await elem.get_attribute('data-testid')
                    if testid and ('tweet' in testid.lower() or 'post' in testid.lower() or 'compose' in testid.lower()):
                        tweet_related_testids.append(testid)
                except Exception as e:
                    self.logger.warning(f"⚠️ Error getting testid: {e}")
                    continue
        
            if tweet_related_testids:
                self.logger.info(f"🐦 Tweet-related testids found: {tweet_related_testids}")
        
            # Tüm aria-label elementler
            aria_elements = await self.page.query_selector_all('[aria-label]')
            self.logger.info(f"🏷️ Found {len(aria_elements)} elements with aria-label")
        
            tweet_related_arias = []
            for elem in aria_elements:
                try:
                    aria_label = await elem.get_attribute('aria-label')
                    if aria_label and ('tweet' in aria_label.lower() or 'post' in aria_label.lower() or 'compose' in aria_label.lower()):
                        tweet_related_arias.append(aria_label)
                except Exception as e:
                    self.logger.warning(f"⚠️ Error getting aria-label: {e}")
                    continue
        
            if tweet_related_arias:
                self.logger.info(f"🐦 Tweet-related aria-labels found: {tweet_related_arias}")
        
            # Tüm link elementler
            links = await self.page.query_selector_all('a[href]')
            self.logger.info(f"🔗 Found {len(links)} link elements")
        
            compose_links = []
            for link in links:
                try:
                    href = await link.get_attribute('href')
                    if href and ('compose' in href or 'tweet' in href or 'post' in href):
                        compose_links.append(href)
                except Exception as e:
                    self.logger.warning(f"⚠️ Error getting href: {e}")
                    continue
        
            if compose_links:
                self.logger.info(f"✍️ Compose-related links found: {compose_links}")
        
            # Tüm button elementler
            buttons = await self.page.query_selector_all('button, div[role="button"], a[role="button"]')
            self.logger.info(f"🔘 Found {len(buttons)} button elements")
        
            # Navigation elementleri
            nav_elements = await self.page.query_selector_all('nav, [role="navigation"]')
            self.logger.info(f"🧭 Found {len(nav_elements)} navigation elements")
        
            # Sidebar elementleri
            sidebar_elements = await self.page.query_selector_all('[data-testid*="sidebar"], [data-testid*="nav"]')
            self.logger.info(f"📋 Found {len(sidebar_elements)} sidebar/nav elements")
        
            for i, elem in enumerate(sidebar_elements[:3]):
                try:
                    testid = await elem.get_attribute('data-testid') or 'No testid'
                    self.logger.info(f"   Sidebar {i+1}: data-testid='{testid}'")
                except Exception as e:
                    self.logger.warning(f"⚠️ Error getting sidebar testid: {e}")
                    continue
                
        except Exception as e:
            self.logger.error(f"❌ Debug failed: {e}")
