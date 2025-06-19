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
        self.last_login_check = 0
        self.login_check_interval = 3600  # 1 saat - daha az agresif
        self.email_handler = EmailHandler()
        self.setup_logging()
        
        # Modern Playwright Selectors - Semantik Öncelikli
        self.selectors = {
            'login': {
                'username_semantic': 'input[autocomplete="username"]',
                'username_fallback': ['input[name="text"]', 'input[type="text"]'],
                'password_semantic': 'input[type="password"]',
                'password_fallback': ['input[name="password"]'],
                'login_button': ['div[data-testid="LoginForm_Login_Button"]', 'button:has-text("Log in")', 'button:has-text("Next")']
            },
            'compose': {
                'tweet_button_semantic': 'a[data-testid="SideNav_NewTweet_Button"]',
                'tweet_button_fallback': [
                    'div[data-testid="SideNav_NewTweet_Button"]',
                    'button[data-testid="SideNav_NewTweet_Button"]',
                    'a[aria-label="Post"]',
                    'button[aria-label="Post"]'
                ],
                'compose_area_semantic': 'div[data-testid="tweetTextarea_0"]',
                'compose_area_fallback': [
                    'div[contenteditable="true"][aria-label*="What"]',
                    'div[contenteditable="true"][role="textbox"]',
                    'div[contenteditable="true"]'
                ],
                'post_button_semantic': 'div[data-testid="tweetButton"]',
                'post_button_fallback': [
                    'button[data-testid="tweetButton"]',
                    'button[role="button"][aria-label*="Post"]'
                ]
            },
            'thread': {
                'add_button_semantic': 'div[aria-label="Add another post"]',
                'add_button_fallback': [
                    'div[aria-label="Add another Tweet"]',
                    'button[aria-label="Add post"]',
                    'div[data-testid="addButton"]'
                ]
            },
            'reply': {
                'reply_button_semantic': 'div[data-testid="reply"]',
                'reply_area_semantic': 'div[data-testid="tweetTextarea_0"]',
                'send_button_semantic': 'div[data-testid="tweetButton"]'
            }
        }
        
    def setup_logging(self):
        """Loglama ayarlarını yapılandır"""
        self.logger = logging.getLogger('TwitterBrowser')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    async def find_element_with_fallback(self, selector_group: str, element_type: str, timeout: int = 5000):
        """Modern selector yaklaşımı - semantik öncelikli, fallback ile"""
        try:
            selectors = self.selectors.get(selector_group, {})
            
            # Önce semantik selector'ı dene
            semantic_key = f"{element_type}_semantic"
            if semantic_key in selectors:
                try:
                    element = await self.page.wait_for_selector(selectors[semantic_key], timeout=timeout)
                    if element and await element.is_visible():
                        self.logger.info(f"✅ Found {element_type} with semantic selector")
                        return element
                except:
                    pass
            
            # Fallback selector'ları dene
            fallback_key = f"{element_type}_fallback"
            if fallback_key in selectors:
                for selector in selectors[fallback_key]:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=timeout)
                        if element and await element.is_visible():
                            self.logger.info(f"✅ Found {element_type} with fallback: {selector}")
                            return element
                    except:
                        continue
            
            self.logger.error(f"❌ Could not find {element_type} in {selector_group}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error finding {element_type}: {e}")
            return None
    
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
    
    async def lightweight_login_check(self):
        """HAFIF login kontrolü - navigasyon yapmadan"""
        try:
            current_time = time.time()
            
            # Çok sık kontrol etme - 1 saatte bir yeterli
            if current_time - self.last_login_check < self.login_check_interval:
                if self.is_logged_in:
                    self.logger.info("⚡ Skipping login check - recently verified")
                    return True
            
            self.logger.info("⚡ Lightweight login check...")
            
            # Mevcut URL'i kontrol et - navigasyon yapma
            current_url = self.page.url
            self.logger.info(f"📍 Current URL: {current_url}")
            
            # Login sayfasındaysak, login olmamışız
            if "login" in current_url or "flow" in current_url:
                self.logger.info("❌ On login page - not logged in")
                self.is_logged_in = False
                return False
            
            # Home sayfasındaysak veya Twitter domain'indeyse
            if "x.com" in current_url or "twitter.com" in current_url:
                if "/home" in current_url or "/compose" in current_url:
                    self.logger.info("✅ On Twitter home/compose - logged in")
                    self.is_logged_in = True
                    self.last_login_check = current_time
                    return True
                
                # Tweet butonu var mı hızlıca kontrol et
                try:
                    tweet_button = await self.page.query_selector('a[data-testid="SideNav_NewTweet_Button"]')
                    if tweet_button:
                        self.logger.info("✅ Tweet button found - logged in")
                        self.is_logged_in = True
                        self.last_login_check = current_time
                        return True
                except:
                    pass
            
            self.logger.info("❌ Login status unclear")
            self.is_logged_in = False
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️ Lightweight check failed: {e}")
            self.is_logged_in = False
            return False
    
    async def full_login_check(self):
        """TAM login kontrolü - sadece gerektiğinde navigasyon yap"""
        try:
            self.logger.info("🔍 Full login check with navigation...")
            
            # Home sayfasına git
            await self.page.goto("https://x.com/home", 
                               wait_until="domcontentloaded", 
                               timeout=15000)
            
            await asyncio.sleep(3)
            
            # URL kontrolü
            current_url = self.page.url
            self.logger.info(f"📍 Current URL after navigation: {current_url}")
            
            # Login sayfasına yönlendirildik mi?
            if "login" in current_url or "flow" in current_url:
                self.logger.info("❌ Redirected to login page - not logged in")
                self.is_logged_in = False
                return False
            
            # Home sayfasındaysak
            if "/home" in current_url:
                self.logger.info("✅ Successfully on home page - logged in")
                self.is_logged_in = True
                self.last_login_check = time.time()
                return True
            
            self.logger.info("❌ Not on expected page")
            self.is_logged_in = False
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️ Full login check failed: {e}")
            self.is_logged_in = False
            return False
    
    async def smart_login_check(self):
        """AKILLI login kontrolü - önce hafif, gerekirse tam"""
        # Önce hafif kontrol
        if await self.lightweight_login_check():
            return True
        
        # Hafif kontrol başarısızsa, tam kontrol
        return await self.full_login_check()
    
    async def direct_login(self):
        """DİREKT ve HIZLI login süreci - Modern Selectors"""
        try:
            self.logger.info("⚡ Starting DIRECT login with modern selectors...")
            self.login_attempts += 1
            self.last_login_attempt = time.time()
            
            # Login sayfasına git
            await self.page.goto("https://twitter.com/i/flow/login", 
                                wait_until="domcontentloaded", 
                                timeout=15000)
            
            await asyncio.sleep(3)
            
            # 1. USERNAME GİR - Modern Approach
            username = os.environ.get('TWITTER_USERNAME') or os.environ.get('EMAIL_USER')
            self.logger.info(f"⚡ Entering username: {username}")
            
            username_field = await self.find_element_with_fallback('login', 'username', timeout=10000)
            if not username_field:
                self.logger.error("❌ Could not find username field")
                return False
            
            await username_field.fill(username)
            await self.page.keyboard.press('Enter')
            self.logger.info("⚡ Username entered and submitted")
            await asyncio.sleep(3)
            
            # 2. USERNAME VERIFICATION (varsa)
            await self.handle_username_verification()
            
            # 3. PASSWORD GİR - Modern Approach
            password = os.environ.get('TWITTER_PASSWORD')
            self.logger.info("⚡ Looking for password field...")
            
            password_field = await self.find_element_with_fallback('login', 'password', timeout=10000)
            if not password_field:
                self.logger.error("❌ Could not find password field")
                return False
            
            await password_field.fill(password)
            await self.page.keyboard.press('Enter')
            self.logger.info("⚡ Password entered and submitted")
            await asyncio.sleep(5)
            
            # 4. EMAIL VERIFICATION (varsa)
            await self.handle_email_verification()
            
            # 5. LOGIN KONTROLÜ
            self.logger.info("🔍 Checking login success...")
            
            # Birkaç kez dene
            for attempt in range(3):
                if await self.full_login_check():
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
        
            # Email'den doğrulama kodunu al
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
        
        # 1. Akıllı login kontrolü
        if await self.smart_login_check():
            return True
        
        # 2. Direkt login süreci
        return await self.direct_login()
    
    async def post_thread(self, content):
        """THREAD OLARAK tweet gönder - AKILLI LOGIN KONTROLÜ"""
        try:
            # SADECE GEREKTİĞİNDE login kontrolü yap
            self.logger.info("🔍 Smart login check before posting...")
            if not await self.lightweight_login_check():
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

            # Mevcut sayfada kalmaya çalış - gereksiz navigasyon yapma
            current_url = self.page.url
            self.logger.info(f"📍 Current URL: {current_url}")
            
            # Sadece login sayfasındaysak home'a git
            if "login" in current_url or "flow" in current_url:
                self.logger.info("🏠 Going to home page...")
                await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
            elif "x.com" not in current_url and "twitter.com" not in current_url:
                self.logger.info("🏠 Going to home page...")
                await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
            else:
                self.logger.info("✅ Already on Twitter, staying on current page")

            # Tweet butonu bul - Modern Approach
            tweet_button = await self.find_element_with_fallback('compose', 'tweet_button', timeout=10000)
            if not tweet_button:
                self.logger.error("❌ Could not find tweet button")
                return False

            # Tweet butonuna tıkla
            await tweet_button.click()
            await asyncio.sleep(3)

            # Compose area bul - Modern Approach
            compose_area = await self.find_element_with_fallback('compose', 'compose_area', timeout=10000)
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
            
                    # Thread butonu bul - Modern Approach
                    thread_button = await self.find_element_with_fallback('thread', 'add_button', timeout=5000)
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
                        except:
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

            # Post butonu bul - Modern Approach
            post_button = await self.find_element_with_fallback('compose', 'post_button', timeout=5000)
            if not post_button:
                self.logger.error("❌ Could not find post button")
                return False

            # Gönder
            await post_button.click()
            await asyncio.sleep(5)

            self.logger.info("🎉 THREAD SUCCESSFULLY POSTED!")
            return True

        except Exception as e:
            self.logger.error(f"❌ Thread posting error: {e}")
            return False
    
    async def get_latest_tweet(self, username):
        """Kullanıcının son tweet'ini al - AKILLI NAVIGASYON"""
        # Hafif login kontrolü
        if not await self.lightweight_login_check():
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
        
            # Tweet'leri bul - Modern Selectors
            tweet_selectors = [
                'article[data-testid="tweet"]',
                'div[data-testid="cellInnerDiv"] article',
                'article[role="article"]',
                '[data-testid="tweet"]'
            ]
        
            first_tweet = None
            for selector in tweet_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    tweets = await self.page.query_selector_all(selector)
                    if tweets:
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
        
            # Tweet metni
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
                        continue
            
                tweet_data['text'] = tweet_text if tweet_text else "No text found"
            
            except Exception as e:
                tweet_data['text'] = "No text found"
        
            # Tweet zamanı
            try:
                time_element = await first_tweet.query_selector('time')
                if time_element:
                    tweet_time = await time_element.get_attribute("datetime")
                    tweet_data['time'] = tweet_time
                else:
                    tweet_data['time'] = None
            except:
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
            except:
                tweet_data['url'] = None
        
            self.logger.info(f"✅ Tweet data retrieved for @{username}")
            self.logger.info(f"📝 Text: {tweet_data['text'][:100]}...")
        
            return tweet_data
        
        except Exception as e:
            self.logger.error(f"❌ Error getting tweet for @{username}: {e}")
            return None
    
    async def get_latest_tweet_id(self, username):
        """Bir kullanıcının son tweet ID'sini al"""
        if not username:
            self.logger.error("❌ Invalid username provided")
            return None
            
        try:
            username = username.strip().replace("@", "")
            
            retries = 3
            for attempt in range(retries):
                try:
                    await self.page.goto(f"https://x.com/{username}", wait_until="domcontentloaded", timeout=40000)
                    await asyncio.sleep(3)
                    break
                except Exception as e:
                    self.logger.warning(f"⚠️ Profile page navigation failed (Attempt {attempt + 1}/{retries}): {e}")
                    if attempt == retries - 1:
                        return None

            tweet_selectors = [
                'article[data-testid="tweet"]',
                '[data-testid="tweet"]',
                'article[role="article"]'
            ]

            for selector in tweet_selectors:
                try:
                    tweets = await self.page.query_selector_all(selector)
                    if tweets and len(tweets) > 0:
                        for tweet in tweets:
                            try:
                                link = await tweet.query_selector('a[href*="/status/"]')
                                if link:
                                    href = await link.get_attribute('href')
                                    if href and '/status/' in href:
                                        tweet_id = href.split('/status/')[1].split('/')[0]
                                        if tweet_id.isalnum():
                                            self.logger.info(f"✅ Found tweet ID: {tweet_id}")
                                            return tweet_id
                            except:
                                continue
                except:
                    continue

            self.logger.error(f"❌ Could not find tweet ID for @{username}")
            return None

        except Exception as e:
            self.logger.error(f"❌ Error getting tweet ID for @{username}: {e}")
            return None
    
    async def reply_to_latest_tweet(self, username, reply_content):
        """Bir kullanıcının son tweetine yanıt ver - AKILLI YAKLAŞIM"""
        # Hafif login kontrolü
        if not await self.lightweight_login_check():
            if not await self.login():
                return False

        try:
            self.logger.info(f"💬 Fetching latest tweet for @{username}...")

            tweet_id = await self.get_latest_tweet_id(username)
            if not tweet_id:
                self.logger.error(f"❌ Could not fetch latest tweet ID for @{username}")
                return False

            tweet_url = f"https://x.com/{username}/status/{tweet_id}"
            self.logger.info(f"💬 Replying to tweet: {tweet_url}")

            await self.page.goto(tweet_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Reply butonu - Modern Approach
            reply_button = await self.find_element_with_fallback('reply', 'reply_button', timeout=10000)
            if not reply_button:
                self.logger.error("❌ Reply button not found!")
                return False

            await reply_button.click()
            await asyncio.sleep(2)

            # Reply area - Modern Approach
            reply_area = await self.find_element_with_fallback('reply', 'reply_area', timeout=10000)
            if not reply_area:
                self.logger.error("❌ Reply area not found!")
                return False

            await reply_area.fill(reply_content)
            await asyncio.sleep(2)

            # Send button - Modern Approach
            send_button = await self.find_element_with_fallback('reply', 'send_button', timeout=10000)
            if not send_button:
                self.logger.error("❌ Send button not found!")
                return False

            await send_button.click()
            await asyncio.sleep(5)
            
            self.logger.info("✅ Reply posted!")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error replying to @{username}: {e}")
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
