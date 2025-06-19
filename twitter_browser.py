from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import asyncio
import time
import os
import json
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from email_handler import EmailHandler  # Ensure this module exists

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
        self.login_cooldown = 1800  # 30 minutes
        self.last_login_check = 0
        self.login_check_interval = 3600  # 1 hour
        self.email_handler = EmailHandler()
        self.setup_logging()
        
        # UPDATED 2025 Twitter Selectors
        self.selectors = {
            'login': {
                'username_semantic': 'input[autocomplete="username"]',
                'username_fallback': ['input[name="text"]', 'input[type="text"]'],
                'password_semantic': 'input[type="password"]',
                'password_fallback': ['input[name="password"]'],
                'login_button': ['div[data-testid="LoginForm_Login_Button"]', 'button:has-text("Log in")', 'button:has-text("Next")']
            },
            'compose': {
                # UPDATED tweet composition selectors
                'tweet_button_semantic': 'div[aria-label="Tweet text"]',
                'tweet_button_fallback': [
                    'div[data-testid="tweetTextarea_0"]',
                    'div[contenteditable="true"][aria-label*="What"]',
                    'div[contenteditable="true"][role="textbox"]',
                    'div[contenteditable="true"]',
                    'div[aria-label="Post text"]',
                    'div[role="textbox"]',
                    'div[data-testid="tweetBox"]'
                ],
                # UPDATED post button selectors
                'post_button_semantic': 'div[data-testid="tweetButtonInline"]',
                'post_button_fallback': [
                    'div[data-testid="tweetButton"]',
                    'button[data-testid="tweetButton"]',
                    'button[data-testid="tweetButtonInline"]',
                    'button[role="button"]:has-text("Post")',
                    'div[role="button"]:has-text("Post")',
                    'button:has-text("Tweet")',
                    'div:has-text("Tweet")',
                    'button:has-text("Send")'
                ]
            },
            'thread': {
                'add_button_semantic': 'div[data-testid="addTweetButton"]',
                'add_button_fallback': [
                    'div[aria-label="Add another post"]',
                    'div[aria-label="Add another Tweet"]',
                    'button[aria-label="Add post"]',
                    'div[data-testid="addButton"]',
                    'button:has-text("+")',
                    'div[data-testid="attachMediaButton"]'  # Alternative button
                ]
            },
            'reply': {
                'reply_button_semantic': 'div[data-testid="reply"]',
                'reply_area_semantic': 'div[data-testid="tweetTextarea_0"]',
                'send_button_semantic': 'div[data-testid="tweetButton"]'
            },
            'popups': {
                'cookie_banner': 'div[role="dialog"]:has-text("Cookies")',
                'cookie_accept': 'button:has-text("Accept")',
                'notification_dialog': 'div[aria-label="Close"]'
            }
        }

    def setup_logging(self):
        """Configure logging settings"""
        self.logger = logging.getLogger('TwitterBrowser')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    async def close_popups(self):
        """Close any popups/dialogs that might obstruct interaction"""
        try:
            # Cookie banner
            try:
                cookie_banner = await self.page.wait_for_selector(
                    self.selectors['popups']['cookie_banner'], 
                    timeout=3000
                )
                if cookie_banner:
                    accept_button = await cookie_banner.wait_for_selector(
                        self.selectors['popups']['cookie_accept'],
                        timeout=2000
                    )
                    if accept_button:
                        await accept_button.click()
                        self.logger.info("✅ Closed cookie banner")
                        await asyncio.sleep(1)
            except:
                pass
            
            # Notification dialog
            try:
                close_button = await self.page.wait_for_selector(
                    self.selectors['popups']['notification_dialog'],
                    timeout=2000
                )
                if close_button:
                    await close_button.click()
                    self.logger.info("✅ Closed notification dialog")
                    await asyncio.sleep(1)
            except:
                pass
        except Exception as e:
            self.logger.warning(f"⚠️ Error closing popups: {e}")

    async def find_element(self, selectors: list, timeout: int = 7000) -> Optional[Page.ElementHandle]:
        """Find element using multiple selectors with fallback"""
        for selector in selectors:
            try:
                self.logger.info(f"🔍 Trying selector: {selector}")
                element = await self.page.wait_for_selector(selector, timeout=timeout)
                if element:
                    is_visible = await element.is_visible()
                    is_enabled = await element.is_enabled()
                    
                    if is_visible and is_enabled:
                        self.logger.info(f"✅ Found element: {selector}")
                        return element
                    else:
                        self.logger.warning(f"⚠️ Element found but not visible/enabled: {selector}")
            except Exception as e:
                self.logger.warning(f"⚠️ Selector failed: {selector} - {str(e)[:70]}")
                continue
        
        self.logger.error(f"❌ Could not find element with selectors: {selectors}")
        return None

    async def initialize(self):
        """Launch Playwright + Chromium"""
        try:
            self.logger.info("🚀 Initializing Playwright + Chromium...")
            
            os.makedirs('data', exist_ok=True)
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-extensions',
                    '--disable-plugins',
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
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            """)
            
            self.page = await self.browser.new_page()
            self.logger.info("✅ Playwright + Chromium initialized!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Initialization error: {str(e)[:200]}")
            return False

    async def check_login_state(self) -> bool:
        """Check if we're logged in without heavy navigation"""
        try:
            current_time = time.time()
            
            # Skip if recently checked
            if current_time - self.last_login_check < 600:  # 10 minutes
                if self.is_logged_in:
                    self.logger.info("⚡ Skipping login check - recently verified")
                    return True
            
            self.logger.info("🔍 Performing login state check...")
            
            # Check current URL
            current_url = self.page.url
            self.logger.info(f"📍 Current URL: {current_url}")
            
            # Check for login indicators
            if "/login" in current_url or "/flow" in current_url:
                self.logger.info("❌ On login page - not logged in")
                self.is_logged_in = False
                return False
            
            # Check for home page elements
            if "x.com" in current_url or "twitter.com" in current_url:
                try:
                    # Check for tweet button
                    tweet_button_selectors = [
                        'a[href="/compose/tweet"]',
                        'div[data-testid="tweetButtonInline"]',
                        'a[data-testid="SideNav_NewTweet_Button"]'
                    ]
                    
                    for selector in tweet_button_selectors:
                        try:
                            if await self.page.query_selector(selector):
                                self.logger.info(f"✅ Found tweet button ({selector}) - logged in")
                                self.is_logged_in = True
                                self.last_login_check = current_time
                                return True
                        except:
                            continue
                except:
                    pass
                
                # Check for sidebar navigation
                try:
                    if await self.page.query_selector('nav[aria-label="Primary"]'):
                        self.logger.info("✅ Found primary navigation - logged in")
                        self.is_logged_in = True
                        self.last_login_check = current_time
                        return True
                except:
                    pass
            
            self.logger.info("❌ Login status unclear, need full check")
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️ Login state check error: {str(e)[:100]}")
            return False

    async def full_login_check(self) -> bool:
        """Perform full login verification with navigation"""
        try:
            self.logger.info("🔍 Performing full login verification...")
            await self.page.goto("https://x.com/home", wait_until="networkidle", timeout=20000)
            await asyncio.sleep(3)
            
            current_url = self.page.url
            self.logger.info(f"📍 Current URL: {current_url}")
            
            if "/home" in current_url:
                self.logger.info("✅ On home page - logged in")
                self.is_logged_in = True
                self.last_login_check = time.time()
                return True
            
            if "/login" in current_url or "/flow" in current_url:
                self.logger.info("❌ Redirected to login page - not logged in")
                self.is_logged_in = False
                return False
            
            # Final check for elements
            try:
                if await self.page.query_selector('div[data-testid="tweetButton"]'):
                    self.logger.info("✅ Found tweet button - logged in")
                    self.is_logged_in = True
                    self.last_login_check = time.time()
                    return True
            except:
                pass
            
            self.logger.info("❌ Not logged in")
            self.is_logged_in = False
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Full login check error: {str(e)[:200]}")
            return False

    async def login(self) -> bool:
        """Perform login with modern selectors"""
        try:
            self.logger.info("🔐 Attempting login...")
            
            # Navigate to login page
            await self.page.goto("https://x.com/i/flow/login", 
                                wait_until="networkidle", 
                                timeout=20000)
            await asyncio.sleep(3)
            
            # Enter username
            username = os.environ.get('TWITTER_USERNAME') or os.environ.get('EMAIL_USER')
            self.logger.info(f"🔑 Entering username: {username}")
            
            username_selectors = [
                self.selectors['login']['username_semantic'],
                *self.selectors['login']['username_fallback']
            ]
            
            username_field = await self.find_element(username_selectors, 10000)
            if not username_field:
                self.logger.error("❌ Username field not found")
                return False
                
            await username_field.fill(username)
            await self.page.keyboard.press('Enter')
            await asyncio.sleep(3)
            
            # Handle potential username verification
            try:
                verification_selectors = [
                    'input[data-testid="ocfEnterTextTextInput"]',
                    'input[autocomplete="current-password"]'
                ]
                verification_field = await self.find_element(verification_selectors, 3000)
                if verification_field:
                    self.logger.info("🔒 Entering username verification")
                    await verification_field.fill(username)
                    await self.page.keyboard.press('Enter')
                    await asyncio.sleep(3)
            except:
                pass
            
            # Enter password
            password = os.environ.get('TWITTER_PASSWORD')
            password_selectors = [
                self.selectors['login']['password_semantic'],
                *self.selectors['login']['password_fallback']
            ]
            
            password_field = await self.find_element(password_selectors, 10000)
            if not password_field:
                self.logger.error("❌ Password field not found")
                return False
                
            await password_field.fill(password)
            await self.page.keyboard.press('Enter')
            await asyncio.sleep(5)
            
            # Check for successful login
            if await self.full_login_check():
                self.logger.info("🎉 Login successful!")
                await self.close_popups()
                return True
                
            self.logger.error("❌ Login verification failed")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Login error: {str(e)[:200]}")
            return False

    async def ensure_logged_in(self) -> bool:
        """Ensure we're logged in with proper state management"""
        if await self.check_login_state():
            return True
            
        if await self.full_login_check():
            return True
            
        return await self.login()

    async def post_thread(self, content) -> bool:
        """Post a thread of tweets with robust element finding"""
        try:
            # Ensure login state
            if not await self.ensure_logged_in():
                self.logger.error("❌ Not logged in, cannot post")
                return False

            # Prepare content
            if isinstance(content, str):
                tweets = self.smart_split_content(content, 270)
            elif isinstance(content, list):
                tweets = [t[:270] for t in content if t]
            else:
                tweets = [str(content)[:270]]
            
            if not tweets:
                self.logger.error("❌ No valid tweets to post")
                return False
                
            self.logger.info(f"🧵 Posting thread with {len(tweets)} tweets")
            
            # Navigate to reliable compose location
            await self.page.goto("https://x.com/compose/tweet", 
                                wait_until="networkidle", 
                                timeout=20000)
            await asyncio.sleep(3)
            await self.close_popups()
            
            # Find compose area
            compose_selectors = [
                *self.selectors['compose']['tweet_button_fallback'],
                self.selectors['compose']['tweet_button_semantic']
            ]
            compose_area = await self.find_element(compose_selectors, 10000)
            if not compose_area:
                self.logger.error("❌ Compose area not found")
                return False
                
            # Enter first tweet
            await compose_area.click()
            await asyncio.sleep(1)
            await compose_area.fill(tweets[0])
            self.logger.info(f"📝 First tweet entered: {tweets[0][:50]}...")
            await asyncio.sleep(2)
            
            # Add additional tweets
            for i, tweet in enumerate(tweets[1:], 1):
                self.logger.info(f"➕ Adding tweet {i+1}/{len(tweets)}")
                
                # Find add tweet button
                add_button_selectors = [
                    *self.selectors['thread']['add_button_fallback'],
                    self.selectors['thread']['add_button_semantic']
                ]
                add_button = await self.find_element(add_button_selectors, 5000)
                if not add_button:
                    self.logger.warning("⚠️ Add button not found, posting as single tweet")
                    break
                    
                await add_button.click()
                await asyncio.sleep(2)
                
                # Find new compose area
                new_compose_selectors = [
                    f'div[data-testid="tweetTextarea_{i}"]',
                    *compose_selectors
                ]
                new_compose = await self.find_element(new_compose_selectors, 5000)
                if not new_compose:
                    self.logger.warning("⚠️ New compose area not found, skipping")
                    continue
                    
                await new_compose.fill(tweet)
                self.logger.info(f"📝 Tweet {i+1} entered")
                await asyncio.sleep(1)
            
            # Find post button
            post_button_selectors = [
                *self.selectors['compose']['post_button_fallback'],
                self.selectors['compose']['post_button_semantic']
            ]
            post_button = await self.find_element(post_button_selectors, 5000)
            if not post_button:
                self.logger.error("❌ Post button not found")
                return False
                
            await post_button.click()
            self.logger.info("✅ Thread posted!")
            await asyncio.sleep(5)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Thread posting failed: {str(e)[:200]}")
            return False

    def smart_split_content(self, content: str, max_length: int = 270) -> List[str]:
        """Improved content splitting with thread numbering"""
        if len(content) <= max_length:
            return [content]
        
        # Split by paragraphs first
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if not paragraphs:
            paragraphs = [content]
        
        tweets = []
        current_tweet = ""
        
        for paragraph in paragraphs:
            # Process long paragraphs
            if len(paragraph) > max_length:
                sentences = [s.strip() + '.' for s in paragraph.split('.') if s.strip()]
                for sentence in sentences:
                    if len(current_tweet) + len(sentence) + 1 <= max_length:
                        current_tweet += f" {sentence}" if current_tweet else sentence
                    else:
                        if current_tweet:
                            tweets.append(current_tweet)
                        current_tweet = sentence
            else:
                if len(current_tweet) + len(paragraph) + 2 <= max_length:
                    current_tweet += f"\n\n{paragraph}" if current_tweet else paragraph
                else:
                    if current_tweet:
                        tweets.append(current_tweet)
                    current_tweet = paragraph
        
        if current_tweet:
            tweets.append(current_tweet)
        
        # Add thread numbering
        if len(tweets) > 1:
            for i, tweet in enumerate(tweets):
                prefix = f"{i+1}/{len(tweets)} "
                if len(prefix + tweet) <= max_length:
                    tweets[i] = prefix + tweet
                else:
                    # Truncate if needed
                    max_tweet = max_length - len(prefix) - 3
                    tweets[i] = prefix + tweet[:max_tweet] + "..."
        
        return tweets

    async def get_latest_tweet(self, username: str) -> Optional[Dict]:
        """Get latest tweet with robust selectors"""
        try:
            if not await self.ensure_logged_in():
                return None
                
            self.logger.info(f"🔍 Getting latest tweet for @{username}")
            await self.page.goto(f"https://x.com/{username}", 
                                wait_until="networkidle", 
                                timeout=30000)
            await asyncio.sleep(3)
            await self.close_popups()
            
            # Find tweets using multiple selectors
            tweet_selectors = [
                'article[data-testid="tweet"]',
                'div[data-testid="cellInnerDiv"] article',
                'article[role="article"]',
                'div[data-testid="tweet"]'
            ]
            
            tweet = None
            for selector in tweet_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    tweets = await self.page.query_selector_all(selector)
                    if tweets:
                        tweet = tweets[0]
                        self.logger.info(f"✅ Found {len(tweets)} tweets with {selector}")
                        break
                except:
                    continue
            
            if not tweet:
                self.logger.warning("⚠️ No tweets found")
                return None
            
            # Extract tweet data
            tweet_data = {'username': username}
            
            # Extract text
            text_selectors = [
                'div[data-testid="tweetText"]',
                'div[lang]',
                'div[dir="auto"]'
            ]
            for selector in text_selectors:
                try:
                    text_elem = await tweet.query_selector(selector)
                    if text_elem:
                        tweet_data['text'] = await text_elem.inner_text()
                        break
                except:
                    continue
            tweet_data['text'] = tweet_data.get('text', '')
            
            # Extract timestamp
            try:
                time_elem = await tweet.query_selector('time')
                if time_elem:
                    tweet_data['time'] = await time_elem.get_attribute('datetime')
            except:
                tweet_data['time'] = None
            
            # Extract URL
            try:
                link_elem = await tweet.query_selector('a[href*="/status/"]')
                if link_elem:
                    href = await link_elem.get_attribute('href')
                    tweet_data['url'] = f"https://x.com{href}" if href.startswith('/') else href
            except:
                tweet_data['url'] = None
            
            self.logger.info(f"✅ Retrieved tweet: {tweet_data['text'][:50]}...")
            return tweet_data
            
        except Exception as e:
            self.logger.error(f"❌ Tweet retrieval error: {str(e)[:200]}")
            return None

    async def get_tweet_time_difference(self, username: str) -> Optional[timedelta]:
        """Get time difference since last tweet with proper timezone handling"""
        try:
            tweet_data = await self.get_latest_tweet(username)
            if not tweet_data or not tweet_data.get('time'):
                return None
                
            tweet_time_str = tweet_data['time']
            if 'Z' in tweet_time_str:
                tweet_time = datetime.fromisoformat(tweet_time_str.replace('Z', '+00:00'))
            else:
                tweet_time = datetime.fromisoformat(tweet_data['time'])
            
            # Ensure both datetimes are timezone-aware
            current_time = datetime.now(timezone.utc)
            if tweet_time.tzinfo is None:
                tweet_time = tweet_time.replace(tzinfo=timezone.utc)
                
            time_diff = current_time - tweet_time
            self.logger.info(f"⏰ Last tweet from @{username}: {time_diff} ago")
            return time_diff
            
        except Exception as e:
            self.logger.error(f"❌ Time difference error: {str(e)[:200]}")
            return None

    async def close(self):
        """Clean up resources"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.logger.info("🔒 Browser closed successfully")
        except Exception as e:
            self.logger.error(f"❌ Close error: {str(e)[:100]}")
