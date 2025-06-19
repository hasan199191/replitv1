from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, ElementHandle
import asyncio
import time
import os
import json
import logging
import random
import re
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
        self.login_check_interval = 3600  # 1 saat
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
    
    async def find_first_locator(self, locator_getters, timeout=5000):
        """Locator bulma fonksiyonu - DÜZELTİLMİŞ"""
        for i, get_locator in enumerate(locator_getters):
            try:
            # Lambda kontrolünü düzelt
                if callable(get_locator):
                    locator = get_locator()
                else:
                    locator = get_locator
            
                self.logger.info(f"🔍 Trying locator {i+1}/{len(locator_getters)}")
                first_locator = locator.first()
                await first_locator.wait_for(state="visible", timeout=timeout)
                self.logger.info(f"✅ Found element with locator {i+1}")
                return first_locator
            except PlaywrightTimeoutError:
                self.logger.warning(f"⚠️ Locator {i+1} timeout")
                continue
            except Exception as e:
                self.logger.warning(f"⚠️ Locator {i+1} failed: {e}")
                continue
        raise Exception("Element bulunamadı")
    
    async def open_tweet_compose(self):
        """Tweet penceresini açma - 2025 MODERN SELECTORS"""
        try:
            self.logger.info("🔍 Opening tweet compose dialog...")
            await asyncio.sleep(2)
    
        # MODERN 2025 selectors - lambda'sız
            compose_btn = await self.find_first_locator([
                self.page.locator('[data-testid="SideNav_NewTweet_Button"]'),
                self.page.locator('a[data-testid="SideNav_NewTweet_Button"]'),
                self.page.locator('div[data-testid="SideNav_NewTweet_Button"]'),
                self.page.locator('a[href="/compose/tweet"]'),
                self.page.locator('[aria-label*="Tweet"]'),
                self.page.locator('[aria-label*="Post"]'),
                self.page.locator('div[contenteditable="true"]'),
                self.page.locator('div[data-testid="tweetTextarea_0"]'),
                self.page.locator('div[role="textbox"]'),
            ], timeout=15000)

            await compose_btn.click()
            await asyncio.sleep(3)
            self.logger.info("✅ Tweet compose dialog opened")
            return compose_btn

        except Exception as e:
            self.logger.error(f"❌ Could not open tweet compose: {e}")
        
            try:
                self.logger.info("🔍 DEBUG: Checking page state...")
                current_url = self.page.url
                self.logger.info(f"📍 Current URL: {current_url}")
            
            # Login sayfasındaysak, tekrar login dene
                if "login" in current_url or "flow" in current_url:
                    self.logger.warning("⚠️ Redirected to login page, attempting re-login...")
                    if await self.login():
                        self.logger.info("✅ Re-login successful, retrying compose...")
                        return await self.open_tweet_compose()
                    else:
                        self.logger.error("❌ Re-login failed")
                        return None
            
                await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
            
                all_buttons = await self.page.locator('button, a, div[role="button"], div[contenteditable="true"]').all()
                self.logger.info(f"📊 Found {len(all_buttons)} clickable elements")
            
                for i, element in enumerate(all_buttons[:10]):
                    try:
                        tag_name = await element.evaluate('el => el.tagName')
                        text = await element.inner_text()
                        self.logger.info(f"Element {i+1}: {tag_name}, text='{text[:30]}'")
                    except Exception:
                        self.logger.warning(f"Element {i+1}: Error getting info")
                    
            except Exception:
                self.logger.warning("⚠️ Enhanced debug failed")

            return None
    
    async def find_tweet_text_area(self):
        """Tweet yazma alanını bul - LAMBDA'SIZ"""
        try:
            self.logger.info("🔍 Looking for tweet text area...")
        
            text_area = await self.find_first_locator([
                self.page.locator('div[data-testid="tweetTextarea_0"]'),
                self.page.locator('div[contenteditable="true"][aria-label*="Tweet"]'),
                self.page.locator('div[contenteditable="true"][role="textbox"]'),
                self.page.locator('div[contenteditable="true"]').first(),
                self.page.locator('div[aria-label="Tweet text"]'),
                self.page.locator('div[role="textbox"]'),
            ], timeout=10000)
        
            self.logger.info("✅ Found tweet text area")
            return text_area
        
        except Exception as e:
            self.logger.error(f"❌ Could not find tweet text area: {e}")
            return None
    
    async def fill_tweet(self, text_area, text: str):
        """Tweet'i yazma"""
        try:
            await text_area.fill(text)
            self.logger.info(f"✅ Tweet text filled: {text[:50]}...")
            return True
        except Exception as e:
            self.logger.error(f"❌ Could not fill tweet: {e}")
            return False
    
    async def send_tweet(self):
        """Tweet'i gönderme - LAMBDA'SIZ"""
        try:
            self.logger.info("🔍 Looking for send button...")
        
            send_btn = await self.find_first_locator([
                self.page.locator('div[data-testid="tweetButtonInline"]'),
                self.page.locator('div[data-testid="tweetButton"]'),
                self.page.locator('button[data-testid="tweetButton"]'),
                self.page.locator('button[data-testid="tweetButtonInline"]'),
                self.page.locator('button:has-text("Post")'),
                self.page.locator('button:has-text("Tweet")'),
                self.page.locator('div[role="button"]:has-text("Post")'),
            ], timeout=10000)
        
            await send_btn.click()
            await asyncio.sleep(5)
        
            self.logger.info("✅ Tweet sent!")
            return True
        
        except Exception as e:
            self.logger.error(f"❌ Could not send tweet: {e}")
            return False
    
    async def thread_tweet(self, texts: List[str]):
        """Thread atma - LAMBDA'SIZ"""
        try:
            self.logger.info(f"🧵 Creating thread with {len(texts)} tweets")
        
            compose_area = await self.open_tweet_compose()
            if not compose_area:
                return False
        
            text_area = await self.find_tweet_text_area()
            if not text_area:
                text_area = compose_area
        
            await self.fill_tweet(text_area, texts[0])
        
            for i, text in enumerate(texts[1:], start=1):
                self.logger.info(f"➕ Adding tweet {i+1}/{len(texts)}")
            
                try:
                    add_btn = await self.find_first_locator([
                        self.page.locator('div[data-testid="addButton"]'),
                        self.page.locator('button[data-testid="addButton"]'),
                        self.page.locator('div[data-testid="addTweetButton"]'),
                        self.page.locator('button[data-testid="addTweetButton"]'),
                        self.page.locator('div[aria-label="Add another post"]'),
                        self.page.locator('div[aria-label="Add another Tweet"]'),
                        self.page.locator('button[aria-label="Add post"]'),
                        self.page.locator('button:has-text("+")'),
                        self.page.locator('div:has-text("+")'),
                    ], timeout=5000)
                
                    await add_btn.click()
                    await asyncio.sleep(3)
                
                    new_text_area = await self.find_first_locator([
                        self.page.locator(f'div[data-testid="tweetTextarea_{i}"]'),
                        self.page.locator('div[contenteditable="true"]').last(),
                        self.page.locator('div[role="textbox"]').last(),
                        self.page.locator('div[aria-label="Tweet text"]').last(),
                    ], timeout=5000)
                
                    await self.fill_tweet(new_text_area, text)
                
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not add tweet {i+1}: {e}")
                    break
        
            return await self.send_tweet()
        
        except Exception as e:
            self.logger.error(f"❌ Thread creation failed: {e}")
            return False
    
    def smart_split_content(self, content: str, max_length: int = 270) -> List[str]:
        """İçeriği akıllı şekilde tweet'lere böl"""
        if not content:
            return []
        
        if len(content) <= max_length:
            return [content]
        
        tweets = []
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if not paragraphs:
            paragraphs = [content]
        
        current_tweet = ""
        tweet_number = 1
        
        for paragraph in paragraphs:
            if len(paragraph) > max_length:
                sentences = [s.strip() + '.' for s in paragraph.split('.') if s.strip()]
                
                for sentence in sentences:
                    thread_prefix = f"{tweet_number}/X "
                    available_space = max_length - len(thread_prefix) - 10
                    
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
                        if len(current_tweet + " " + sentence) <= available_space:
                            current_tweet += (" " + sentence if current_tweet else sentence)
                        else:
                            if current_tweet:
                                tweets.append(current_tweet)
                                tweet_number += 1
                            current_tweet = sentence
            else:
                thread_prefix = f"{tweet_number}/X "
                available_space = max_length - len(thread_prefix) - 10
                
                if len(current_tweet + " " + paragraph) <= available_space:
                    current_tweet += (" " + paragraph if current_tweet else paragraph)
                else:
                    if current_tweet:
                        tweets.append(current_tweet)
                        tweet_number += 1
                    current_tweet = paragraph
        
        if current_tweet:
            tweets.append(current_tweet)
        
        total_tweets = len(tweets)
        if total_tweets > 1:
            for i in range(total_tweets):
                tweets[i] = f"{i+1}/{total_tweets} {tweets[i]}"
                
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
        """HAFIF login kontrolü"""
        try:
            current_time = time.time()
        
            if current_time - self.last_login_check < 1800:
                if self.is_logged_in:
                    self.logger.info("⚡ Skipping login check - recently verified")
                    return True
        
            self.logger.info("⚡ Lightweight login check...")
        
            current_url = self.page.url
            self.logger.info(f"📍 Current URL: {current_url}")
        
            if "login" in current_url or "flow" in current_url:
                self.logger.info("❌ On login page - not logged in")
                self.is_logged_in = False
                return False
        
            if "x.com" in current_url or "twitter.com" in current_url:
                if "/home" in current_url or "/compose" in current_url:
                    self.logger.info("✅ On Twitter home/compose - logged in")
                    self.is_logged_in = True
                    self.last_login_check = current_time
                    return True
            
            try:
                tweet_area = await self.page.locator('div[contenteditable="true"]').first().count()
                if tweet_area > 0:
                    self.logger.info("✅ Tweet area found - logged in")
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
        """TAM login kontrolü"""
        try:
            self.logger.info("🔍 Full login check with navigation...")
            
            await self.page.goto("https://x.com/home", 
                               wait_until="domcontentloaded", 
                               timeout=15000)
            
            await asyncio.sleep(3)
            
            current_url = self.page.url
            self.logger.info(f"📍 Current URL after navigation: {current_url}")
            
            if "login" in current_url or "flow" in current_url:
                self.logger.info("❌ Redirected to login page - not logged in")
                self.is_logged_in = False
                return False
            
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
        """AKILLI login kontrolü"""
        if await self.lightweight_login_check():
            return True
        
        return await self.full_login_check()
    
    async def direct_login(self):
        """DİREKT login süreci"""
        try:
            self.logger.info("⚡ Starting DIRECT login...")
            self.login_attempts += 1
            self.last_login_attempt = time.time()
            
            await self.page.goto("https://twitter.com/i/flow/login", 
                                wait_until="domcontentloaded", 
                                timeout=15000)
            
            await asyncio.sleep(3)
            
            username = os.environ.get('TWITTER_USERNAME') or os.environ.get('EMAIL_USER')
            self.logger.info(f"⚡ Entering username: {username}")
            
            try:
                username_field = await self.find_first_locator([
                    lambda: self.page.locator('input[autocomplete="username"]'),
                    lambda: self.page.locator('input[name="text"]'),
                    lambda: self.page.locator('input[type="text"]'),
                ], timeout=10000)
                
                await username_field.fill(username)
                await self.page.keyboard.press('Enter')
                self.logger.info("⚡ Username entered and submitted")
                await asyncio.sleep(3)
            except Exception as e:
                self.logger.error(f"❌ Could not find username field: {e}")
                return False
            
            await self.handle_username_verification()
            
            password = os.environ.get('TWITTER_PASSWORD')
            self.logger.info("⚡ Looking for password field...")
            
            try:
                password_field = await self.find_first_locator([
                    lambda: self.page.locator('input[type="password"]'),
                    lambda: self.page.locator('input[name="password"]'),
                ], timeout=10000)
                
                await password_field.fill(password)
                await self.page.keyboard.press('Enter')
                self.logger.info("⚡ Password entered and submitted")
                await asyncio.sleep(5)
            except Exception as e:
                self.logger.error(f"❌ Could not find password field: {e}")
                return False
            
            await self.handle_email_verification()
            
            self.logger.info("🔍 Checking login success...")
            
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
        """Username verification"""
        try:
            try:
                element = await self.page.wait_for_selector(
                    'input[data-testid="ocfEnterTextTextInput"]', 
                    timeout=3000
                )
                if element:
                    username = os.environ.get('TWITTER_USERNAME')
                    await element.fill(username)
                    self.logger.info(f"⚡ Username verification: {username}")
                    
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
        """Email verification"""
        try:
            self.logger.info("🔍 Checking for email verification...")
        
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
        
            verification_code = self.email_handler.get_twitter_verification_code(timeout=90)
        
            if verification_code:
                self.logger.info(f"✅ Got verification code: {verification_code}")
            
                await verification_input.fill(verification_code)
                await asyncio.sleep(1)
            
                await self.page.keyboard.press('Enter')
                self.logger.info("✅ Verification code submitted")
            
                await asyncio.sleep(5)
                return True
            else:
                self.logger.error("❌ Could not get verification code from email")
                await asyncio.sleep(60)
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
        
        if await self.smart_login_check():
            return True
        
        return await self.direct_login()
    
    async def post_thread(self, content):
        """THREAD OLARAK tweet gönder"""
        try:
            self.logger.info("🔍 Smart login check before posting...")
            if not await self.lightweight_login_check():
                self.logger.warning("❌ Not logged in, attempting login...")
                if not await self.login():
                    self.logger.error("❌ Login failed, cannot post thread")
                    return False
    
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

            current_url = self.page.url
            self.logger.info(f"📍 Current URL: {current_url}")
            
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

            return await self.thread_tweet(tweets)

        except Exception as e:
            self.logger.error(f"❌ Thread posting error: {e}")
            return False
    
    async def get_latest_tweet(self, username):
        """Kullanıcının son tweet'ini al"""
        if not await self.lightweight_login_check():
            if not await self.login():
                return None

        try:
            self.logger.info(f"🔍 Getting latest tweet for @{username}")

            profile_url = f"https://x.com/{username}"
            await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            current_url = self.page.url
            if "login" in current_url or "flow" in current_url:
                self.logger.error(f"❌ Redirected to login when accessing @{username}")
                return None

            try:
                all_tweets = await self.page.locator('article[data-testid="tweet"]').all()
                self.logger.info(f"📊 Found {len(all_tweets)} tweets for @{username}")

                if not all_tweets:
                    self.logger.warning(f"⚠️ No tweets found for @{username}")
                    return None

                first_tweet = all_tweets[0]

                try:
                    pinned_indicator = await first_tweet.locator('[data-testid="socialContext"]').count()
                    if pinned_indicator > 0:
                        self.logger.info(f"📌 Skipping pinned tweet for @{username}")
                        if len(all_tweets) > 1:
                            first_tweet = all_tweets[1]
                        else:
                            self.logger.warning(f"⚠️ Only pinned tweet found for @{username}")
                            return None
                except:
                    pass
                
            except Exception as e:
                self.logger.warning(f"⚠️ No tweets found for @{username}: {e}")
                return None

            tweet_data = {'username': username}

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
                        text_elements = await first_tweet.locator(selector).all()
                        if text_elements:
                            text_parts = []
                            for elem in text_elements:
                                text = await elem.inner_text()
                                if text and text.strip():
                                    text_parts.append(text.strip())
                            if text_parts:
                                tweet_text = " ".join(text_parts)
                                break
                    except Exception:
                        continue

                tweet_data['text'] = tweet_text if tweet_text else "No text found"

            except Exception:
                tweet_data['text'] = "No text found"

            try:
                time_element = await first_tweet.locator('time').first()
                if time_element:
                    tweet_time = await time_element.get_attribute("datetime")
                    tweet_data['time'] = tweet_time
                else:
                    tweet_data['time'] = None
            except:
                tweet_data['time'] = None

            try:
                link_element = await first_tweet.locator('a[href*="/status/"]').first()
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

            try:
                first_tweet = await self.find_first_locator([
                    lambda: self.page.get_by_role("article"),
                    lambda: self.page.locator('article[data-testid="tweet"]'),
                    lambda: self.page.locator('[data-testid="tweet"]'),
                    lambda: self.page.locator('article[role="article"]')
                ], timeout=10000)
                
                link = await first_tweet.query_selector('a[href*="/status/"]')
                if link:
                    href = await link.get_attribute('href')
                    if href and '/status/' in href:
                        tweet_id = href.split('/status/')[1].split('/')[0]
                        if tweet_id.isalnum():
                            self.logger.info(f"✅ Found tweet ID: {tweet_id}")
                            return tweet_id
            except Exception as e:
                self.logger.error(f"❌ Could not find tweet ID for @{username}: {e}")
                return None

            self.logger.error(f"❌ Could not find tweet ID for @{username}")
            return None

        except Exception as e:
            self.logger.error(f"❌ Error getting tweet ID for @{username}: {e}")
            return None
    
    async def reply_to_latest_tweet(self, username, reply_content):
        """Bir kullanıcının son tweetine yanıt ver"""
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

            try:
                reply_btn = await self.find_first_locator([
                    lambda: self.page.get_by_role("button", name=re.compile(r"yorum yap|reply", re.I)),
                    lambda: self.page.locator('div[data-testid^="reply"]'),
                    lambda: self.page.locator('div[data-testid="reply"]'),
                ], timeout=10000)
                
                await reply_btn.click()
                await asyncio.sleep(2)
            except Exception as e:
                self.logger.error(f"❌ Reply button not found: {e}")
                return False

            try:
                reply_box = await self.find_first_locator([
                    lambda: self.page.get_by_role("textbox", name=re.compile(r"tweet'e yanıtla|reply", re.I)),
                    lambda: self.page.locator('div[contenteditable="true"][aria-label*="Reply"]'),
                    lambda: self.page.locator('div[data-testid="tweetTextarea_0"]'),
                    lambda: self.page.locator('div[contenteditable="true"]'),
                ], timeout=10000)
                
                await reply_box.fill(reply_content)
                await asyncio.sleep(2)
            except Exception as e:
                self.logger.error(f"❌ Reply area not found: {e}")
                return False

            try:
                send_btn = await self.find_first_locator([
                    lambda: self.page.get_by_role("button", name=re.compile(r"tweetle|reply", re.I)),
                    lambda: self.page.locator('div[data-testid="tweetButton"]'),
                    lambda: self.page.locator('button[data-testid="tweetButton"]'),
                ], timeout=10000)
                
                await send_btn.click()
                await asyncio.sleep(5)
                
                self.logger.info("✅ Reply posted!")
                return True
            except Exception as e:
                self.logger.error(f"❌ Send button not found: {e}")
                return False

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
