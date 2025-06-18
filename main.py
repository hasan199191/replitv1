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
import re

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

class EmailHandler:
    def __init__(self):
        self.email = os.getenv('EMAIL_ADDRESS')
        self.password = os.getenv('EMAIL_PASSWORD')
        logging.info(f"📧 Email Handler initialized for: {self.email}")
        
    async def get_verification_code(self, timeout=120):
        """Gmail'den X.com doğrulama kodunu al"""
        try:
            logging.info("📧 Gmail'e bağlanıyor...")
            
            # Gmail IMAP bağlantısı
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(self.email, self.password)
            logging.info("✅ Gmail'e başarıyla bağlandı")
            
            mail.select('inbox')
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # Son 5 dakikadaki emailleri ara - daha kısa süre
                    since_date = (datetime.now() - timedelta(minutes=5)).strftime("%d-%b-%Y")
                    
                    # X.com'dan gelen emailleri ara - kesin kriterler
                    search_criteria = f'(FROM "info@x.com" SUBJECT "Your X confirmation code") SINCE {since_date}'
                    
                    result, messages = mail.search(None, search_criteria)
                    
                    if messages[0]:
                        email_ids = messages[0].split()
                        logging.info(f"📧 {len(email_ids)} X confirmation email bulundu")
                        
                        # En son emaili al
                        latest_email_id = email_ids[-1]
                        
                        # Email içeriğini al
                        result, msg_data = mail.fetch(latest_email_id, '(RFC822)')
                        email_body = msg_data[0][1]
                        
                        # Email'i parse et
                        email_message = email.message_from_bytes(email_body)
                        
                        # Subject kontrol et
                        subject = email_message.get('Subject', '')
                        sender = email_message.get('From', '')
                        date = email_message.get('Date', '')
                        
                        logging.info(f"📧 Email bulundu - Subject: {subject}")
                        logging.info(f"📧 Sender: {sender}")
                        
                        # Subject'den doğrudan kodu çıkar
                        if "Your X confirmation code is " in subject:
                            # Subject: "Your X confirmation code is 6saz54wc"
                            code_from_subject = subject.replace("Your X confirmation code is ", "").strip()
                            if len(code_from_subject) >= 6 and len(code_from_subject) <= 8:
                                logging.info(f"✅ Subject'den kod alındı: {code_from_subject}")
                                mail.logout()
                                return code_from_subject
                        
                        # Email içeriğini de kontrol et
                        body = ""
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                    break
                        else:
                            body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                        
                        logging.info(f"📧 Email içeriği: {body[:200]}...")
                        
                        # İçerikten kodu bul - tam format
                        code_patterns = [
                            r'single-use code\.\s*([a-zA-Z0-9]{6,8})',  # "single-use code. 6saz54wc"
                            r'entering the following.*?([a-zA-Z0-9]{6,8})',  # "entering the following... 6saz54wc"
                            r'\n([a-zA-Z0-9]{6,8})\n',  # Tek satırda olan kod
                            r'^([a-zA-Z0-9]{6,8})$',  # Tek başına satırda olan kod
                        ]
                        
                        for pattern in code_patterns:
                            matches = re.findall(pattern, body, re.MULTILINE | re.IGNORECASE)
                            for match in matches:
                                # Alfanumerik ve 6-8 karakter kontrol
                                if len(match) >= 6 and len(match) <= 8 and re.match(r'^[a-zA-Z0-9]+$', match):
                                    # En az bir harf ve bir rakam içermeli
                                    if re.search(r'[a-zA-Z]', match) and re.search(r'[0-9]', match):
                                        logging.info(f"✅ İçerikten X doğrulama kodu bulundu: {match}")
                                        mail.logout()
                                        return match.lower()
                        
                        # Basit regex - body'deki tüm alfanumerik 8 karakterli stringler
                        simple_codes = re.findall(r'\b([a-zA-Z0-9]{8})\b', body)
                        for code in simple_codes:
                            if re.search(r'[a-zA-Z]', code) and re.search(r'[0-9]', code):
                                logging.info(f"✅ Basit regex ile kod bulundu: {code}")
                                mail.logout()
                                return code.lower()
                        
                        logging.info("📧 Email bulundu ama kod parse edilemedi")
                        
                    else:
                        logging.info("📧 X confirmation emaili bulunamadı, bekleniyor...")
                    
                    await asyncio.sleep(8)  # 8 saniye bekle
                    
                except Exception as e:
                    logging.error(f"❌ Email kontrol hatası: {e}")
                    await asyncio.sleep(8)
            
            mail.logout()
            logging.warning("⚠️ Timeout: X doğrulama kodu bulunamadı")
            return None
            
        except Exception as e:
            logging.error(f"❌ Gmail bağlantı hatası: {e}")
            return None

class ContentGenerator:
    def __init__(self):
        self.model = None
        
    def initialize(self):
        try:
            # Gemini API anahtarını al
            gemini_api_key = os.getenv('GEMINI_API_KEY')
            if not gemini_api_key:
                logging.error("Error initializing Gemini Flash 2.0: Gemini API key not found")
                return False
                
            # Gemini'yi yapılandır
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            
            logging.info("Advanced Gemini Flash 2.0 successfully initialized")
            return True
            
        except Exception as e:
            logging.error(f"Error initializing Gemini: {e}")
            return False
            
    def generate_content(self, prompt):
        try:
            if not self.model:
                return "Content generator not initialized"
                
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logging.error(f"Error generating content: {e}")
            return "Error generating content"

class TwitterBrowser:
    def __init__(self, username, password, email_handler=None):
        self.username = username
        self.password = password
        self.email_handler = email_handler
        self.playwright = None
        self.browser = None
        self.page = None
        
    async def initialize(self):
        try:
            logging.info('🚀 Initializing Playwright + Chrome...')
            self.playwright = await async_playwright().start()
            
            # Chrome'u gerçek tarayıcı gibi göster
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                channel="chrome",  # Gerçek Chrome kullan
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--exclude-switches=enable-automation',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-extensions-except',
                    '--disable-plugins-discovery',
                    '--start-maximized',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            )
            
            # Context oluştur - bot tespitini engelle
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Cache-Control': 'max-age=0'
                }
            )
            
            self.page = await context.new_page()
            
            # Bot tespitini engelle
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                window.chrome = {
                    runtime: {},
                };
                
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({ state: 'granted' }),
                    }),
                });
            """)
            
            logging.info('✅ Chrome initialized!')
            return True
            
        except Exception as e:
            logging.error(f'❌ Failed to initialize Chrome: {e}')
            return False
            
    async def quick_login_check(self):
        try:
            logging.info('⚡ Quick login check...')
            await self.page.goto('https://x.com/home', wait_until='networkidle')
            await asyncio.sleep(5)
            
            current_url = self.page.url.lower()
            
            # Eğer login sayfasına yönlendirildiyse, giriş yapılmamış demektir
            if 'login' in current_url or 'signin' in current_url or 'flow' in current_url:
                logging.info('❌ Not logged in - redirected to login page')
                return False
            
            # Ana sayfa, compose veya dashboard'daysa giriş yapılmış demektir
            if 'home' in current_url or 'compose' in current_url or 'dashboard' in current_url:
                # Ek kontrol: Tweet butonu var mı?
                try:
                    tweet_button_selectors = [
                        '[data-testid="SideNav_NewTweet_Button"]',
                        '[href="/compose/post"]',
                        'a[aria-label*="Post"]',
                        'button[aria-label*="Post"]'
                    ]
                    
                    for selector in tweet_button_selectors:
                        if await self.page.locator(selector).count() > 0:
                            logging.info('✅ Already logged in - tweet button found')
                            return True
                    
                    logging.info('❌ Not logged in - no tweet button found')
                    return False
                    
                except:
                    logging.info('❌ Not logged in - unable to verify login elements')
                    return False
            
            logging.info('❌ Not logged in - unknown page')
            return False
                
        except Exception as e:
            logging.error(f'❌ Quick login check failed: {e}')
            return False

    async def check_login_success(self, page):
        try:
            await asyncio.sleep(3)
            current_url = page.url.lower()
            
            # Login sayfalarında değilse kontrol et
            if 'login' not in current_url and 'signin' not in current_url and 'flow' not in current_url:
                # Tweet butonu veya ana sayfa elementlerini ara
                success_elements = [
                    '[data-testid="SideNav_NewTweet_Button"]',
                    '[href="/compose/post"]',
                    '[data-testid="primaryColumn"]',
                    '[aria-label="Home timeline"]'
                ]
                
                for selector in success_elements:
                    try:
                        if await page.locator(selector).count() > 0:
                            logging.info('✅ Login successful!')
                            return True
                    except:
                        continue
            
            # Başarısız giriş kontrolleri
            failure_indicators = ['login', 'signin', 'error', 'suspended', 'flow']
            for indicator in failure_indicators:
                if indicator in current_url:
                    logging.info(f'❌ Login failed - on {indicator} page')
                    return False
                    
            logging.info('❌ Login status unclear')
            return False
            
        except Exception as e:
            logging.error(f'❌ Login check error: {e}')
            return False
            
    async def quick_login_check(self):
        try:
            logging.info('⚡ Quick login check...')
            await self.page.goto('https://x.com/home', wait_until='networkidle')
            await asyncio.sleep(5)
            
            current_url = self.page.url.lower()
            
            # Eğer login sayfasına yönlendirildiyse, giriş yapılmamış demektir
            if 'login' in current_url or 'signin' in current_url or 'flow' in current_url:
                logging.info('❌ Not logged in - redirected to login page')
                return False
            
            # Ana sayfa, compose veya dashboard'daysa giriş yapılmış demektir
            if 'home' in current_url or 'compose' in current_url or 'dashboard' in current_url:
                # Ek kontrol: Tweet butonu var mı?
                try:
                    tweet_button_selectors = [
                        '[data-testid="SideNav_NewTweet_Button"]',
                        '[href="/compose/post"]',
                        'a[aria-label*="Post"]',
                        'button[aria-label*="Post"]'
                    ]
                    
                    for selector in tweet_button_selectors:
                        if await self.page.locator(selector).count() > 0:
                            logging.info('✅ Already logged in - tweet button found')
                            return True
                    
                    logging.info('❌ Not logged in - no tweet button found')
                    return False
                    
                except:
                    logging.info('❌ Not logged in - unable to verify login elements')
                    return False
            
            logging.info('❌ Not logged in - unknown page')
            return False
                
        except Exception as e:
            logging.error(f'❌ Quick login check failed: {e}')
            return False

    async def check_login_success(self, page):
        try:
            await asyncio.sleep(3)
            current_url = page.url.lower()
            
            # Login sayfalarında değilse kontrol et
            if 'login' not in current_url and 'signin' not in current_url and 'flow' not in current_url:
                # Tweet butonu veya ana sayfa elementlerini ara
                success_elements = [
                    '[data-testid="SideNav_NewTweet_Button"]',
                    '[href="/compose/post"]',
                    '[data-testid="primaryColumn"]',
                    '[aria-label="Home timeline"]'
                ]
                
                for selector in success_elements:
                    try:
                        if await page.locator(selector).count() > 0:
                            logging.info('✅ Login successful!')
                            return True
                    except:
                        continue
            
            # Başarısız giriş kontrolleri
            failure_indicators = ['login', 'signin', 'error', 'suspended', 'flow']
            for indicator in failure_indicators:
                if indicator in current_url:
                    logging.info(f'❌ Login failed - on {indicator} page')
                    return False
                    
            logging.info('❌ Login status unclear')
            return False
            
        except Exception as e:
            logging.error(f'❌ Login check error: {e}')
            return False
            
    async def manual_verification_input(self, page):
        """Manuel doğrulama kodu girişi"""
        try:
            print("\n" + "="*60)
            print("🔐 EMAIL DOĞRULAMA KODU GEREKİYOR")
            print("="*60)
            print(f"📧 Gmail hesabınızı kontrol edin: {self.email_handler.email}")
            print("🔍 'X (Twitter)' veya 'verify@twitter.com' dan gelen emaili bulun")
            print("📝 6-8 haneli doğrulama kodunu kopyalayın")
            print("="*60)
            
            verification_code = input("📧 Doğrulama kodunu girin: ").strip()
            
            if verification_code:
                logging.info(f"✅ Kod giriliyor: {verification_code}")
                
                # Birden fazla selector dene
                selectors = [
                    'input[data-testid="ocfEnterTextTextInput"]',
                    'input[name="text"]',
                    'input[type="text"]',
                    'input[placeholder*="code"]'
                ]
                
                for selector in selectors:
                    try:
                        code_input = page.locator(selector)
                        if await code_input.count() > 0:
                            await code_input.fill(verification_code)
                            await asyncio.sleep(1)
                            await page.keyboard.press('Enter')
                            await asyncio.sleep(3)
                            
                            if await self.check_login_success(page):
                                logging.info("✅ Manuel doğrulama başarılı!")
                                return True
                            break
                    except:
                        continue
                        
                logging.error("❌ Doğrulama kodu girişi başarısız")
                return False
            else:
                logging.error("❌ Doğrulama kodu girilmedi")
                return False
                
        except Exception as e:
            logging.error(f"❌ Manuel doğrulama hatası: {e}")
            return False
            
    async def direct_login(self):
        try:
            page = self.page
            logging.info('⚡ Starting login to X.com...')
            
            # X.com giriş sayfasına git
            await page.goto('https://x.com/i/flow/login', wait_until='networkidle')
            await asyncio.sleep(5)
            
            # İnsan gibi davranış - random beklemeler
            await asyncio.sleep(random.uniform(2, 4))
            
            # Username gir
            username_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[data-testid="ocfEnterTextTextInput"]'
            ]
            
            username_entered = False
            for selector in username_selectors:
                try:
                    username_input = page.locator(selector)
                    if await username_input.count() > 0:
                        await username_input.click()
                        await asyncio.sleep(1)
                        await username_input.fill(self.username)
                        logging.info(f'⚡ Username entered: {self.username}')
                        await asyncio.sleep(1)
                        await page.keyboard.press('Enter')
                        username_entered = True
                        break
                except:
                    continue
                    
            if not username_entered:
                logging.error("❌ Could not enter username")
                return False
                
            await asyncio.sleep(5)
            
            # Password gir
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[autocomplete="current-password"]'
            ]
            
            password_entered = False
            for selector in password_selectors:
                try:
                    password_input = page.locator(selector)
                    if await password_input.count() > 0:
                        await password_input.click()
                        await asyncio.sleep(1)
                        await password_input.fill(self.password)
                        logging.info('⚡ Password entered')
                        await asyncio.sleep(1)
                        await page.keyboard.press('Enter')
                        password_entered = True
                        break
                except:
                    continue
                    
            if not password_entered:
                logging.error("❌ Could not enter password")
                return False
                
            await asyncio.sleep(5)
            
            # Email doğrulama kontrolü
            email_verification_required = False
            try:
                verification_selectors = [
                    'input[data-testid="ocfEnterTextTextInput"]',
                    'input[name="text"]',
                    'input[placeholder*="confirmation"]',
                    'input[placeholder*="verification"]'
                ]
                
                for selector in verification_selectors:
                    if await page.locator(selector).count() > 0:
                        email_verification_required = True
                        break
                        
            except:
                pass
            
            if email_verification_required:
                logging.info('📧 Email doğrulama gerekiyor - otomatik kod alınıyor...')
                
                # Gmail bilgilerini kontrol et
                logging.info(f"📧 Email Handler durumu:")
                logging.info(f"   - Email: {self.email_handler.email}")
                logging.info(f"   - Password: {'✅ Set' if self.email_handler.password else '❌ Not set'}")
                logging.info(f"   - Password length: {len(self.email_handler.password) if self.email_handler.password else 0}")
                
                # Gmail'den kodu otomatik al
                if self.email_handler and self.email_handler.email and self.email_handler.password:
                    logging.info("🔄 Gmail'den kod alınıyor...")
                    
                    code = await self.email_handler.get_verification_code(timeout=90)
                    
                    if code:
                        logging.info(f'✅ Gmail\'den kod alındı: {code}')
                        
                        # Kodu gir
                        try:
                            code_input = page.locator('input[data-testid="ocfEnterTextTextInput"]')
                            await code_input.fill(str(code))
                            await asyncio.sleep(1)
                            await page.keyboard.press('Enter')
                            await asyncio.sleep(3)
                            
                            # Giriş başarısını kontrol et
                            if await self.check_login_success(page):
                                logging.info('✅ Otomatik email doğrulama ile giriş başarılı!')
                                return True
                            else:
                                logging.warning("⚠️ Kod girildi ama giriş başarısız, manuel deneniyor...")
                                return await self.manual_verification_input(page)
                                
                        except Exception as e:
                            logging.error(f"❌ Kod girme hatası: {e}")
                            return await self.manual_verification_input(page)
                            
                    else:
                        logging.warning("❌ Gmail'den kod alınamadı, manuel girişe geçiliyor...")
                        return await self.manual_verification_input(page)
                else:
                    logging.error("❌ Gmail bilgileri eksik!")
                    return await self.manual_verification_input(page)
            
            # Normal giriş kontrolü
            return await self.check_login_success(page)
            
        except Exception as e:
            logging.error(f"❌ Login error: {e}")
            return False
            
    async def login(self):
        if await self.quick_login_check():
            return True
        return await self.direct_login()
        
    async def cleanup(self):
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logging.error(f'Cleanup error: {e}')

class TwitterBot:
    def __init__(self):
        self.initialization_attempts = 0
        self.max_init_attempts = 3
        self.bot_start_time = datetime.now()
        self.content_generator = ContentGenerator()
        self.email_handler = EmailHandler()
        self.browser = None
        self.last_action_time = time.time()
        
    async def initialize(self):
        self.initialization_attempts += 1
        logging.info(f"🤖 Initializing Twitter Bot (Attempt {self.initialization_attempts}/{self.max_init_attempts})...")
        logging.info(f"🕐 Bot start time: {self.bot_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Load data
        if not self.load_data():
            return False
            
        # Initialize content generator
        if not self.content_generator.initialize():
            return False
            
        logging.info("🧠 Content generator initialized")
        
        # Initialize browser
        username = os.getenv('TWITTER_USERNAME')
        password = os.getenv('TWITTER_PASSWORD')
        
        if not username or not password:
            logging.error("❌ Twitter credentials not found in .env file")
            return False
            
        self.browser = TwitterBrowser(username, password, self.email_handler)
        
        if not await self.browser.initialize():
            return False
            
        # Login
        if not await self.browser.login():
            logging.error("❌ Login failed")
            return False
            
        logging.info("✅ Bot initialization successful!")
        return True
        
    def load_data(self):
        try:
            # Mock data loading
            projects_count = 34
            accounts_count = 53
            logging.info(f"Data loaded: {projects_count} projects, {accounts_count} accounts")
            return True
        except Exception as e:  # "as e" eksikti
            logging.error(f"Error loading data: {e}")
            return False
            
    async def perform_bot_tasks(self):
        """Bot görevlerini yerine getir"""
        try:
            current_time = time.time()
            
            # Her 30 dakikada bir tweet at
            if current_time - self.last_action_time > 1800:  # 30 dakika = 1800 saniye
                await self.post_tweet()
                self.last_action_time = current_time
                
            # Diğer görevler eklenebilir:
            # - Beğeni, retweet
            # - DM gönderme
            # - Trend takibi
            
        except Exception as e:
            logging.error(f"❌ Bot görev hatası: {e}")
            
    async def post_tweet(self):
        """Tweet gönder"""
        try:
            logging.info("📝 Tweet hazırlanıyor...")
            
            # Gemini ile içerik üret
            prompt = "Kripto para ile ilgili güncel, ilgi çekici ve kısa bir tweet oluştur. Maksimum 200 karakter olsun."
            content = self.content_generator.generate_content(prompt)
            
            if len(content) > 200:
                content = content[:197] + "..."
                
            logging.info(f"📝 Tweet içeriği: {content}")
            
            # Tweet gönder
            await self.browser.page.goto('https://x.com/compose/post', wait_until='networkidle')
            await asyncio.sleep(3)
            
            # Tweet alanını bul ve içerik yaz
            tweet_selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[contenteditable="true"]',
                'div[role="textbox"]'
            ]
            
            for selector in tweet_selectors:
                try:
                    tweet_box = self.browser.page.locator(selector)
                    if await tweet_box.count() > 0:
                        await tweet_box.click()
                        await asyncio.sleep(1)
                        await tweet_box.fill(content)
                        await asyncio.sleep(2)
                        
                        # Tweet gönder butonuna tıkla
                        post_button = self.browser.page.locator('[data-testid="tweetButton"]')
                        if await post_button.count() > 0:
                            await post_button.click()
                            await asyncio.sleep(3)
                            logging.info("✅ Tweet gönderildi!")
                            return True
                        break
                except:
                    continue
                    
            logging.error("❌ Tweet gönderilemedi")
            return False
            
        except Exception as e:
            logging.error(f"❌ Tweet gönderme hatası: {e}")
            return False
    
    async def run(self):
        while self.initialization_attempts < self.max_init_attempts:
            if await self.initialize():
                logging.info("🎉 Bot is now running...")
                
                # Ana bot döngüsü
                try:
                    self.last_action_time = time.time()
                    
                    while True:
                        await asyncio.sleep(300)  # 5 dakika bekle
                        logging.info("🔄 Bot is active...")
                        
                        # Bot görevlerini yap
                        await self.perform_bot_tasks()
                        
                except KeyboardInterrupt:
                    logging.info("🛑 Bot stopped by user")
                    break
                    
            else:
                if self.initialization_attempts >= self.max_init_attempts:
                    logging.error(f"❌ Failed to initialize after {self.max_init_attempts} attempts")
                    break
                else:
                    logging.warning(f"⚠️ Initialization failed, retrying in 30 seconds...")
                    await asyncio.sleep(30)
                    
        # Cleanup
        if self.browser:
            await self.browser.cleanup()

async def main():
    bot = TwitterBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
