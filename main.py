import asyncio
import logging
import os
import sys
import time
import json
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai
from playwright.async_api import async_playwright
import imaplib
import email
from advanced_content_generator import AdvancedContentGenerator
from health_server import start_health_server
import threading
from email_handler import EmailHandler

# Windows konsol kodlama sorununu çöz
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Load environment variables
load_dotenv()

# logs klasörünü oluştur (eğer yoksa)
if not os.path.exists('logs'):
    os.makedirs('logs')

# Logging konfigürasyonu - UTF-8 encoding ile
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class TwitterBrowser:
    def __init__(self, username, password, email_handler=None, content_generator=None):
        self.username = username
        self.password = password
        self.email_handler = email_handler
        self.content_generator = content_generator
        self.playwright = None
        self.context = None
        self.page = None
        self.user_data_dir = "/tmp/playwright_data"
        self.is_logged_in = False
        self.login_attempts = 0
        self.max_login_attempts = 3

    async def initialize(self):
        try:
            logging.info("🚀 Initializing browser...")
            
            # Klasörü oluştur
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            self.playwright = await async_playwright().start()
            
            # Browser launch with optimized settings
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--disable-hang-monitor',
                    '--disable-client-side-phishing-detection',
                    '--disable-component-update',
                    '--no-zygote',
                    '--single-process'
                ]
            )
            
            # Anti-detection
            await self.context.add_init_script("""
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
            
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
                
            # Set longer timeouts
            self.page.set_default_timeout(90000)  # 90 seconds
            
            logging.info("✅ Browser initialized successfully!")
            return True
            
        except Exception as e:
            logging.error(f"❌ Browser initialization failed: {e}")
            return False

    async def safe_goto(self, url, retries=3):
        """Safe navigation with retries"""
        for attempt in range(retries):
            try:
                logging.info(f"🌐 Navigating to {url} (attempt {attempt + 1}/{retries})")
                await self.page.goto(url, wait_until="domcontentloaded", timeout=90000)
                await asyncio.sleep(3)
                return True
            except Exception as e:
                logging.warning(f"⚠️ Navigation attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                else:
                    logging.error(f"❌ All navigation attempts failed for {url}")
                    return False
        return False

    async def check_if_logged_in(self):
        """Comprehensive login status check"""
        try:
            logging.info("🔍 Checking login status...")
            
            # Navigate to home page
            if not await self.safe_goto("https://x.com/home"):
                return False
            
            await asyncio.sleep(5)
            
            current_url = self.page.url.lower()
            logging.info(f"📍 Current URL: {current_url}")
            
            # Check if redirected to login
            if any(keyword in current_url for keyword in ['login', 'signin', 'flow']):
                logging.info("❌ Redirected to login page - not logged in")
                return False
            
            # Check for login indicators
            login_indicators = [
                '[data-testid="SideNav_NewTweet_Button"]',
                '[data-testid="tweetButton"]',
                '[aria-label="Post"]',
                '[href="/compose/post"]',
                '[data-testid="primaryColumn"]',
                'nav[aria-label="Primary"]',
                '[data-testid="AppTabBar_Home_Link"]'
            ]
            
            for selector in login_indicators:
                try:
                    element_count = await self.page.locator(selector).count()
                    if element_count > 0:
                        logging.info(f"✅ Login confirmed - found {selector}")
                        self.is_logged_in = True
                        return True
                except:
                    continue
            
            # Check page title
            try:
                title = await self.page.title()
                if 'home' in title.lower() and 'login' not in title.lower():
                    logging.info("✅ Login confirmed by page title")
                    self.is_logged_in = True
                    return True
            except:
                pass
            
            # Check for profile menu
            try:
                profile_menu = await self.page.locator('[data-testid="SideNav_AccountSwitcher_Button"]').count()
                if profile_menu > 0:
                    logging.info("✅ Login confirmed - profile menu found")
                    self.is_logged_in = True
                    return True
            except:
                pass
            
            logging.info("❌ No login indicators found")
            return False
            
        except Exception as e:
            logging.error(f"❌ Login check error: {e}")
            return False

    async def perform_login(self):
        """Perform login process"""
        try:
            if self.login_attempts >= self.max_login_attempts:
                logging.error("❌ Maximum login attempts reached")
                return False
            
            self.login_attempts += 1
            logging.info(f"🔐 Starting login attempt {self.login_attempts}/{self.max_login_attempts}")
            
            # Navigate to login page
            if not await self.safe_goto("https://x.com/i/flow/login"):
                return False
            
            await asyncio.sleep(5)
            
            # Wait for page to load
            try:
                await self.page.wait_for_selector('input', timeout=30000)
                logging.info("✅ Login page loaded")
            except:
                logging.error("❌ Login page failed to load")
                return False
            
            # Enter username
            username_entered = False
            username_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[data-testid="ocfEnterTextTextInput"]',
                'input[type="text"]'
            ]
            
            for selector in username_selectors:
                try:
                    logging.info(f"🔍 Trying username selector: {selector}")
                    element = await self.page.wait_for_selector(selector, timeout=10000)
                    if element and await element.is_visible():
                        await element.click()
                        await asyncio.sleep(1)
                        await element.fill('')
                        await asyncio.sleep(0.5)
                        await element.type(self.username, delay=100)
                        logging.info(f"✅ Username entered: {self.username}")
                        await asyncio.sleep(2)
                        await self.page.keyboard.press('Enter')
                        username_entered = True
                        break
                except Exception as e:
                    logging.warning(f"⚠️ Username selector {selector} failed: {e}")
                    continue
            
            if not username_entered:
                logging.error("❌ Failed to enter username")
                return False
            
            await asyncio.sleep(5)
            
            # Enter password
            password_entered = False
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[autocomplete="current-password"]'
            ]
            
            for selector in password_selectors:
                try:
                    logging.info(f"🔍 Trying password selector: {selector}")
                    element = await self.page.wait_for_selector(selector, timeout=15000)
                    if element and await element.is_visible():
                        await element.click()
                        await asyncio.sleep(1)
                        await element.fill(self.password)
                        logging.info("✅ Password entered")
                        await asyncio.sleep(2)
                        await self.page.keyboard.press('Enter')
                        password_entered = True
                        break
                except Exception as e:
                    logging.warning(f"⚠️ Password selector {selector} failed: {e}")
                    continue
            
            if not password_entered:
                logging.error("❌ Failed to enter password")
                return False
            
            await asyncio.sleep(10)  # Wait for login processing
            
            # Check for email verification
            verification_needed = False
            try:
                verification_input = await self.page.wait_for_selector(
                    'input[data-testid="ocfEnterTextTextInput"]', 
                    timeout=5000
                )
                if verification_input:
                    verification_needed = True
            except:
                pass
            
            if verification_needed:
                logging.info("📧 Email verification required")
                if await self.handle_email_verification():
                    logging.info("✅ Email verification completed")
                else:
                    logging.error("❌ Email verification failed")
                    return False
            
            # Final login check
            await asyncio.sleep(5)
            if await self.check_if_logged_in():
                logging.info("🎉 Login successful!")
                self.login_attempts = 0  # Reset on success
                return True
            else:
                logging.error("❌ Login failed - not detected as logged in")
                return False
                
        except Exception as e:
            logging.error(f"❌ Login process error: {e}")
            return False

    async def handle_email_verification(self):
        """Handle email verification"""
        try:
            logging.info("📧 Handling email verification...")
            
            if not self.email_handler:
                logging.error("❌ No email handler available")
                return False
            
            # Get verification code from email - use async version
            verification_code = await self.email_handler.get_twitter_verification_code(timeout=120)
        
            if not verification_code:
                logging.error("❌ Could not get verification code")
                return False
        
            logging.info(f"✅ Got verification code: {verification_code}")
        
            # Enter verification code
            try:
                code_input = await self.page.wait_for_selector(
                    'input[data-testid="ocfEnterTextTextInput"]', 
                    timeout=10000
                )
                if code_input:
                    await code_input.fill(str(verification_code))
                    await asyncio.sleep(1)
                    await self.page.keyboard.press('Enter')
                    await asyncio.sleep(5)
                    return True
            except Exception as e:
                logging.error(f"❌ Failed to enter verification code: {e}")
                return False
            
        except Exception as e:
            logging.error(f"❌ Email verification error: {e}")
            return False

    async def login(self):
        """Main login method"""
        try:
            # First check if already logged in
            if await self.check_if_logged_in():
                logging.info("✅ Already logged in!")
                return True
            
            # Perform login
            return await self.perform_login()
            
        except Exception as e:
            logging.error(f"❌ Login method error: {e}")
            return False

    async def post_thread(self, content):
        """Post content as thread"""
        try:
            if not self.is_logged_in:
                if not await self.login():
                    return False
            
            # Process content
            if isinstance(content, str):
                tweets = self.content_generator.split_content_by_sentences(content, char_limit=270)
            elif isinstance(content, list):
                tweets = content
            else:
                logging.error(f"❌ Invalid content type: {type(content)}")
                return False
            
            logging.info(f"📝 Posting thread with {len(tweets)} tweets")
            
            # Navigate to compose
            if not await self.safe_goto("https://x.com/compose/tweet"):
                return False
            
            await asyncio.sleep(3)
            
            # Post each tweet
            for i, tweet_text in enumerate(tweets):
                # Find compose area
                compose_selectors = [
                    "div[data-testid='tweetTextarea_0']",
                    "div[contenteditable='true']",
                    "div[role='textbox']"
                ]
                
                compose_element = None
                for selector in compose_selectors:
                    try:
                        compose_element = await self.page.wait_for_selector(selector, timeout=10000)
                        if compose_element:
                            break
                    except:
                        continue
                
                if not compose_element:
                    logging.error("❌ Could not find compose area")
                    return False
                
                # Enter tweet text
                await compose_element.click()
                await asyncio.sleep(1)
                await compose_element.fill(tweet_text)
                await asyncio.sleep(2)
                
                # Add next tweet if not last
                if i < len(tweets) - 1:
                    add_button_selectors = [
                        "button[data-testid='addButton']",
                        "button[aria-label='Add post']",
                        "div[aria-label='Add post']"
                    ]
                    
                    add_clicked = False
                    for selector in add_button_selectors:
                        try:
                            add_button = await self.page.wait_for_selector(selector, timeout=5000)
                            if add_button:
                                await add_button.click()
                                await asyncio.sleep(3)
                                add_clicked = True
                                logging.info(f"✅ Added tweet {i+1}")
                                break
                        except:
                            continue
                    
                    if not add_clicked:
                        logging.error("❌ Could not add next tweet")
                        return False
            
            # Post the thread
            post_selectors = [
                "div[data-testid='tweetButton']",
                "button[data-testid='tweetButton']"
            ]
            
            for selector in post_selectors:
                try:
                    post_button = await self.page.wait_for_selector(selector, timeout=10000)
                    if post_button:
                        await post_button.click()
                        await asyncio.sleep(5)
                        logging.info("✅ Thread posted successfully!")
                        return True
                except:
                    continue
            
            logging.error("❌ Could not post thread")
            return False
            
        except Exception as e:
            logging.error(f"❌ Thread posting error: {e}")
            return False

    async def reply_to_tweet(self, tweet_id, reply_content):
        """Reply to a tweet"""
        try:
            if not self.is_logged_in:
                if not await self.login():
                    return False
            
            logging.info(f"💬 Replying to tweet: {tweet_id}")
            
            # Navigate to tweet
            if not await self.safe_goto(f"https://x.com/i/web/status/{tweet_id}"):
                return False
            
            await asyncio.sleep(5)
            
            # Click reply button
            reply_selectors = [
                '[data-testid="reply"]',
                'div[data-testid="reply"]',
                'button[data-testid="reply"]'
            ]
            
            reply_clicked = False
            for selector in reply_selectors:
                try:
                    reply_button = await self.page.wait_for_selector(selector, timeout=10000)
                    if reply_button:
                        await reply_button.click()
                        await asyncio.sleep(3)
                        reply_clicked = True
                        break
                except:
                    continue
            
            if not reply_clicked:
                logging.error("❌ Could not click reply button")
                return False
            
            # Enter reply
            reply_area_selectors = [
                'div[data-testid="tweetTextarea_0"]',
                'div[contenteditable="true"]',
                'div[role="textbox"]'
            ]
            
            reply_area = None
            for selector in reply_area_selectors:
                try:
                    reply_area = await self.page.wait_for_selector(selector, timeout=10000)
                    if reply_area:
                        break
                except:
                    continue
            
            if not reply_area:
                logging.error("❌ Could not find reply area")
                return False
            
            await reply_area.click()
            await asyncio.sleep(1)
            await reply_area.fill(reply_content)
            await asyncio.sleep(2)
            
            # Post reply
            post_reply_selectors = [
                '[data-testid="tweetButton"]',
                'div[data-testid="tweetButtonInline"]'
            ]
            
            for selector in post_reply_selectors:
                try:
                    post_button = await self.page.wait_for_selector(selector, timeout=10000)
                    if post_button:
                        await post_button.click()
                        await asyncio.sleep(3)
                        logging.info("✅ Reply posted successfully!")
                        return True
                except:
                    continue
            
            logging.error("❌ Could not post reply")
            return False
            
        except Exception as e:
            logging.error(f"❌ Reply error: {e}")
            return False

    async def get_latest_tweet_id(self, username):
        """Get latest tweet ID for user"""
        try:
            logging.info(f"🔍 Getting latest tweet for @{username}")
            
            if not await self.safe_goto(f"https://x.com/{username}"):
                return None
            
            await asyncio.sleep(8)
            
            # Wait for tweets to load
            try:
                await self.page.wait_for_selector('article[data-testid="tweet"]', timeout=20000)
            except:
                logging.warning("⚠️ No tweets found on profile")
                return None
            
            # Find tweet links
            tweet_links = await self.page.query_selector_all('a[href*="/status/"]')
            
            for link in tweet_links:
                try:
                    href = await link.get_attribute('href')
                    if href and f'/{username}/' in href and '/status/' in href:
                        tweet_id = href.split('/status/')[1].split('/')[0].split('?')[0]
                        if tweet_id.isdigit():
                            logging.info(f"✅ Found tweet ID: {tweet_id}")
                            return tweet_id
                except:
                    continue
            
            logging.warning(f"⚠️ No tweet ID found for @{username}")
            return None
            
        except Exception as e:
            logging.error(f"❌ Error getting tweet ID for @{username}: {e}")
            return None

    async def get_tweet_content(self, tweet_id):
        """Get tweet content"""
        try:
            if not await self.safe_goto(f"https://x.com/i/web/status/{tweet_id}"):
                return None
            
            await asyncio.sleep(3)
            
            content_selectors = [
                '[data-testid="tweetText"]',
                'div[data-testid="tweetText"]'
            ]
            
            for selector in content_selectors:
                try:
                    content_element = await self.page.wait_for_selector(selector, timeout=10000)
                    if content_element:
                        content = await content_element.inner_text()
                        if content:
                            return content.strip()
                except:
                    continue
            
            return None
            
        except Exception as e:
            logging.error(f"❌ Error getting tweet content: {e}")
            return None

    async def get_tweet_time(self, tweet_id):
        """Get tweet timestamp"""
        try:
            # If already on tweet page, don't navigate again
            current_url = self.page.url
            if f"/status/{tweet_id}" not in current_url:
                if not await self.safe_goto(f"https://x.com/i/web/status/{tweet_id}"):
                    return datetime.now()
            
            await asyncio.sleep(2)
            
            time_selectors = [
                'time[datetime]',
                'article time[datetime]'
            ]
            
            for selector in time_selectors:
                try:
                    time_element = await self.page.wait_for_selector(selector, timeout=10000)
                    if time_element:
                        datetime_str = await time_element.get_attribute('datetime')
                        if datetime_str:
                            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                except:
                    continue
            
            # Return current time as fallback
            return datetime.now()
            
        except Exception as e:
            logging.error(f"❌ Error getting tweet time: {e}")
            return datetime.now()

    async def close(self):
        """Close browser"""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            logging.info("🔒 Browser closed")
        except Exception as e:
            logging.error(f"❌ Error closing browser: {e}")

async def main():
    logging.info("🚀 Bot başlatılıyor...")
    print("🚀 Bot başlatılıyor...")

    # Health server'ı başlat (Render için gerekli)
    try:
        health_server = start_health_server()
        logging.info("✅ Health server başlatıldı")
    except Exception as e:
        logging.error(f"❌ Health server başlatılamadı: {e}")

    # Environment variables debug
    logging.info("🔍 Environment variables check:")
    env_vars = ['TWITTER_USERNAME', 'TWITTER_PASSWORD', 'EMAIL_ADDRESS', 'EMAIL_USER', 'EMAIL_PASSWORD', 'GMAIL_APP_PASSWORD', 'EMAIL_PASS', 'GEMINI_API_KEY']
    for var in env_vars:
        value = os.getenv(var)
        logging.info(f"   {var}: {'✅ Set' if value else '❌ Not set'}")

    # Gerekli environment değişkenlerini kontrol et
    TWITTER_USERNAME = os.getenv('TWITTER_USERNAME')
    TWITTER_PASSWORD = os.getenv('TWITTER_PASSWORD')
    if not TWITTER_USERNAME or not TWITTER_PASSWORD:
        logging.error("❌ Twitter kullanıcı adı veya şifre environment variables'da eksik!")
        print("❌ Twitter kullanıcı adı veya şifre environment variables'da eksik!")
        return

    # Email bilgilerini kontrol et
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS') or os.getenv('EMAIL_USER')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD') or os.getenv('GMAIL_APP_PASSWORD') or os.getenv('EMAIL_PASS')
    
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        logging.error("❌ Gmail bilgileri environment variables'da eksik!")
        print("❌ Gmail bilgileri environment variables'da eksik!")
        return
        
    if not os.getenv('GEMINI_API_KEY'):
        logging.error("❌ Gemini API anahtarı environment variables'da eksik!")
        print("❌ Gemini API anahtarı environment variables'da eksik!")
        return

    # Initialize components with retry logic
    max_init_retries = 3
    for attempt in range(max_init_retries):
        try:
            logging.info(f"🔄 Initialization attempt {attempt + 1}/{max_init_retries}")
            
            # Initialize components
            email_handler = EmailHandler()
            content_generator = AdvancedContentGenerator()
            
            if not await content_generator.initialize():
                raise Exception("Gemini initialization failed")
            
            twitter = TwitterBrowser(TWITTER_USERNAME, TWITTER_PASSWORD, email_handler, content_generator)
            
            if not await twitter.initialize():
                raise Exception("Browser initialization failed")
            
            if not await twitter.login():
                raise Exception("Twitter login failed")
            
            logging.info("✅ All components initialized successfully!")
            break
            
        except Exception as e:
            logging.error(f"❌ Initialization attempt {attempt + 1} failed: {e}")
            if attempt < max_init_retries - 1:
                logging.info("⏳ Waiting 30 seconds before retry...")
                await asyncio.sleep(30)
            else:
                logging.error("❌ All initialization attempts failed!")
                return

    # Get data
    projects = content_generator.projects
    accounts = content_generator.monitored_accounts

    logging.info("✅ Bot başlatıldı ve login oldu. Ana döngü başlıyor...")
    print("✅ Bot başlatıldı ve login oldu. Ana döngü başlıyor...")

    # Main loop with error recovery
    consecutive_errors = 0
    max_consecutive_errors = 5

    while True:
        try:
            logging.info("🔄 Starting new cycle...")
            
            # 1. Post project content
            try:
                selected_projects = random.sample(content_generator.projects, 2)
                
                for i, project in enumerate(selected_projects):
                    try:
                        logging.info(f"📝 Generating content for project {i+1}: {project['name']}")
                        content = await content_generator.generate_project_content(project)
                        
                        if content and isinstance(content, list) and len(content) > 0:
                            logging.info(f"✅ Generated {len(content)} tweets for {project['name']}")
                            if await twitter.post_thread(content):
                                logging.info(f"✅ Thread posted for {project['name']}")
                            else:
                                logging.error(f"❌ Failed to post thread for {project['name']}")
                            
                            # Wait between posts
                            await asyncio.sleep(random.uniform(60, 120))
                        else:
                            logging.warning(f"⚠️ No valid content generated for {project['name']}")
                            
                    except Exception as e:
                        logging.error(f"❌ Error with project {project['name']}: {e}")
                        continue
                        
            except Exception as e:
                logging.error(f"❌ Error in project posting: {e}")

            # 2. Reply to monitored accounts
            try:
                reply_count = 0
                max_replies_per_cycle = 3
                
                # Shuffle accounts for variety
                shuffled_accounts = random.sample(accounts, min(10, len(accounts)))
                
                for account in shuffled_accounts:
                    try:
                        if reply_count >= max_replies_per_cycle:
                            break
                        
                        logging.info(f"🔍 Checking @{account}...")
                        
                        tweet_id = await twitter.get_latest_tweet_id(account)
                        if not tweet_id:
                            logging.warning(f"⚠️ No tweet found for @{account}")
                            continue
                        
                        tweet_content = await twitter.get_tweet_content(tweet_id)
                        if not tweet_content:
                            logging.warning(f"⚠️ No content found for tweet {tweet_id}")
                            continue
                        
                        tweet_time = await twitter.get_tweet_time(tweet_id)
                        time_diff = (datetime.now() - tweet_time).total_seconds()
                        
                        if time_diff <= 3600:  # 1 hour
                            logging.info(f"✅ Recent tweet found ({time_diff/60:.1f} min ago)")
                            
                            reply = await content_generator.generate_reply({
                                'text': tweet_content, 
                                'username': account
                            })
                            
                            if reply and isinstance(reply, str):
                                if await twitter.reply_to_tweet(tweet_id, reply):
                                    reply_count += 1
                                    logging.info(f"✅ Reply posted to @{account} ({reply_count}/{max_replies_per_cycle})")
                                    await asyncio.sleep(random.uniform(90, 180))
                                else:
                                    logging.error(f"❌ Failed to reply to @{account}")
                            else:
                                logging.warning(f"⚠️ No valid reply generated for @{account}")
                        else:
                            logging.info(f"ℹ️ Tweet too old ({time_diff/3600:.1f} hours)")
                            
                    except Exception as e:
                        logging.error(f"❌ Error processing @{account}: {e}")
                        continue
                
                logging.info(f"✅ Reply cycle completed. Posted {reply_count} replies.")
                
            except Exception as e:
                logging.error(f"❌ Error in reply cycle: {e}")

            # Reset error counter on successful cycle
            consecutive_errors = 0
            
            # Wait for next cycle
            logging.info("⏳ Waiting 2 hours for next cycle...")
            await asyncio.sleep(2 * 60 * 60)  # 2 hours
            
        except Exception as e:
            consecutive_errors += 1
            logging.error(f"❌ Main loop error ({consecutive_errors}/{max_consecutive_errors}): {e}")
            
            if consecutive_errors >= max_consecutive_errors:
                logging.error("❌ Too many consecutive errors, restarting...")
                try:
                    await twitter.close()
                except:
                    pass
                
                # Wait before restart
                await asyncio.sleep(300)  # 5 minutes
                
                # Restart the whole process
                return await main()
            else:
                # Wait and continue
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
