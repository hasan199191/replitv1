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
        # Environment variable isimlerini düzelt
        self.email = os.getenv('EMAIL_ADDRESS') or os.getenv('EMAIL_USER')
        self.password = os.getenv('EMAIL_PASSWORD') or os.getenv('GMAIL_APP_PASSWORD') or os.getenv('EMAIL_PASS')
        
        # Debug için environment variables'ları logla
        logging.info(f"📧 Environment variables check:")
        logging.info(f"   EMAIL_ADDRESS: {'✅ Set' if os.getenv('EMAIL_ADDRESS') else '❌ Not set'}")
        logging.info(f"   EMAIL_USER: {'✅ Set' if os.getenv('EMAIL_USER') else '❌ Not set'}")
        logging.info(f"   EMAIL_PASSWORD: {'✅ Set' if os.getenv('EMAIL_PASSWORD') else '❌ Not set'}")
        logging.info(f"   GMAIL_APP_PASSWORD: {'✅ Set' if os.getenv('GMAIL_APP_PASSWORD') else '❌ Not set'}")
        logging.info(f"   EMAIL_PASS: {'✅ Set' if os.getenv('EMAIL_PASS') else '❌ Not set'}")
        
        logging.info(f"📧 Email Handler initialized for: {self.email}")
        logging.info(f"📧 Password status: {'✅ Set' if self.password else '❌ Not set'}")
        
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
                    # Son 5 dakikadaki emailleri ara
                    since_date = (datetime.now() - timedelta(minutes=5)).strftime("%d-%b-%Y")
                    
                    # X.com'dan gelen emailleri ara
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
                        
                        logging.info(f"📧 Email bulundu - Subject: {subject}")
                        logging.info(f"📧 Sender: {sender}")
                        
                        # Subject'den doğrudan kodu çıkar
                        if "Your X confirmation code is " in subject:
                            code_from_subject = subject.replace("Your X confirmation code is ", "").strip()
                            if len(code_from_subject) >= 6 and len(code_from_subject) <= 8:
                                logging.info(f"✅ Subject'den kod alındı: {code_from_subject}")
                                mail.logout()
                                return code_from_subject
                        
                    else:
                        logging.info("📧 X confirmation emaili bulunamadı, bekleniyor...")
                    
                    await asyncio.sleep(8)
                    
                except Exception as e:
                    logging.error(f"❌ Email kontrol hatası: {e}")
                    await asyncio.sleep(8)
            
            mail.logout()
            logging.warning("⚠️ Timeout: X doğrulama kodu bulunamadı")
            return None
            
        except Exception as e:
            logging.error(f"❌ Gmail bağlantı hatası: {e}")
            return None

class TwitterBrowser:
    def __init__(self, username, password, email_handler=None, content_generator=None):
        self.username = username
        self.password = password
        self.email_handler = email_handler
        self.content_generator = content_generator
        self.playwright = None
        self.context = None
        self.page = None
        self.user_data_dir = "/tmp/playwright_data"  # Render için /tmp kullan

    async def initialize(self):
        try:
            # Klasörü oluştur
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            self.playwright = await async_playwright().start()
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,  # Render için True
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
                    '--start-maximized',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection'
                ]
            )
            
            # Anti-detection script ekle
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
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({ state: 'granted' })
                    })
                });
            """)
            
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
                
            # Sayfa yükleme timeout'unu artır
            self.page.set_default_timeout(60000)
            
            await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            logging.info("✅ Chrome initialized with persistent profile!")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to initialize Chrome: {e}")
            return False

    async def check_login_success(self, page):
        try:
            await asyncio.sleep(5)  # Daha uzun bekle
            current_url = page.url.lower()
            
            logging.info(f"🔍 Current URL: {current_url}")
            
            # URL kontrolü
            if 'login' not in current_url and 'signin' not in current_url and 'flow' not in current_url:
                # UI element kontrolü
                success_elements = [
                    '[data-testid="SideNav_NewTweet_Button"]',
                    '[href="/compose/post"]',
                    '[data-testid="primaryColumn"]',
                    '[aria-label="Home timeline"]',
                    '[data-testid="AppTabBar_Home_Link"]'
                ]
                
                for selector in success_elements:
                    try:
                        element_count = await page.locator(selector).count()
                        logging.info(f"🔍 Checking {selector}: {element_count} found")
                        if element_count > 0:
                            logging.info('✅ Login successful!')
                            return True
                    except Exception as e:
                        logging.warning(f"⚠️ Error checking {selector}: {e}")
                        continue
                
                # Sayfa başlığı kontrolü
                try:
                    title = await page.title()
                    logging.info(f"🔍 Page title: {title}")
                    if 'home' in title.lower() or 'x.com' in title.lower():
                        logging.info('✅ Login successful (by title)!')
                        return True
                except:
                    pass
            
            # Başarısızlık göstergeleri
            failure_indicators = ['login', 'signin', 'error', 'suspended', 'flow']
            for indicator in failure_indicators:
                if indicator in current_url:
                    logging.info(f'❌ Login failed - on {indicator} page')
                    return False
            
            # Email verification kontrolü
            try:
                verification_elements = await page.locator('input[data-testid="ocfEnterTextTextInput"]').count()
                if verification_elements > 0:
                    logging.info('📧 Email verification required')
                    return False
            except:
                pass
                    
            logging.info('❌ Login status unclear - assuming failed')
            return False
            
        except Exception as e:
            logging.error(f'❌ Login check error: {e}')
            return False
            
    async def quick_login_check(self):
        try:
            logging.info('⚡ Quick login check...')
            for _ in range(2):  # 2 kez dene
                try:
                    await self.page.goto('https://x.com/home', wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(4)
                    break
                except Exception as e:
                    logging.warning(f"Home sayfası yüklenemedi, tekrar deneniyor: {e}")
                    await asyncio.sleep(3)
            current_url = self.page.url.lower()
            if 'login' in current_url or 'signin' in current_url or 'flow' in current_url:
                logging.info('❌ Not logged in - redirected to login page')
                return False
            # Ana sayfa, compose veya dashboard'daysa giriş yapılmış demektir
            if 'home' in current_url or 'compose' in current_url or 'dashboard' in current_url:
                try:
                    tweet_button_selectors = [
                        '[data-testid="SideNav_NewTweet_Button"]',
                        '[href="/compose/post"]',
                        'a[aria-label*="Post"]',
                        'button[aria-label*="Post"]',
                        'a[aria-label*="Tweet"]',
                        'button[aria-label*="Tweet"]',
                        '[data-testid="tweetButtonInline"]'
                    ]
                    for selector in tweet_button_selectors:
                        if await self.page.locator(selector).count() > 0:
                            logging.info('✅ Already logged in - tweet button found')
                            return True
                    logging.info('❌ Not logged in - no tweet button found')
                    return False
                except Exception as e:
                    logging.info(f'❌ Not logged in - unable to verify login elements: {e}')
                    return False
            logging.info('❌ Not logged in - unknown page')
            return False
        except Exception as e:
            logging.error(f'❌ Quick login check failed: {e}')
            return False
            
    async def manual_verification_input(self, page):
        """Manuel doğrulama kodu girişi - Render için otomatik geç"""
        try:
            logging.info("🔐 EMAIL DOĞRULAMA KODU GEREKİYOR")
            logging.info(f"📧 Gmail hesabı kontrol ediliyor: {self.email_handler.email}")
            
            # Render'da manuel giriş yapamayız, otomatik email kontrolü yap
            if self.email_handler and self.email_handler.email and self.email_handler.password:
                logging.info("🔄 Gmail'den otomatik kod alınıyor...")
                
                code = await self.email_handler.get_verification_code(timeout=120)
                
                if code:
                    logging.info(f'✅ Gmail\'den kod alındı: {code}')
                    
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
                                await code_input.fill(str(code))
                                await asyncio.sleep(1)
                                await page.keyboard.press('Enter')
                                await asyncio.sleep(3)
                                
                                if await self.check_login_success(page):
                                    logging.info("✅ Otomatik doğrulama başarılı!")
                                    return True
                                break
                        except:
                            continue
                            
                    logging.error("❌ Doğrulama kodu girişi başarısız")
                    return False
                else:
                    logging.error("❌ Gmail'den kod alınamadı")
                    return False
            else:
                logging.error("❌ Gmail bilgileri eksik!")
                return False
                
        except Exception as e:
            logging.error(f"❌ Otomatik doğrulama hatası: {e}")
            return False
            
    async def direct_login(self):
        try:
            page = self.page
            logging.info('⚡ Starting login to X.com...')
            
            # Login sayfasına git
            await page.goto('https://x.com/i/flow/login', wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)
            
            # Sayfanın tam yüklenmesini bekle
            try:
                await page.wait_for_selector('input', timeout=15000)
                logging.info("✅ Login sayfası yüklendi")
            except:
                logging.error("❌ Login sayfası yüklenemedi")
                return False
            
            await asyncio.sleep(random.uniform(2, 4))
            
            # Username gir - GELİŞTİRİLMİŞ SELECTOR'LAR
            username_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[data-testid="ocfEnterTextTextInput"]',
                'input[type="text"]',
                'input[placeholder*="username"]',
                'input[placeholder*="email"]',
                'input[placeholder*="phone"]'
            ]
            
            username_entered = False
            for i, selector in enumerate(username_selectors):
                try:
                    logging.info(f"🔍 Username selector {i+1}/{len(username_selectors)}: {selector}")
                    
                    # Element'i bekle
                    username_input = await page.wait_for_selector(selector, timeout=8000)
                    if username_input:
                        # Element görünür mü kontrol et
                        is_visible = await username_input.is_visible()
                        if is_visible:
                            logging.info(f"✅ Username alanı bulundu ve görünür: {selector}")
                            
                            # Alana tıkla
                            await username_input.click()
                            await asyncio.sleep(1)
                            
                            # Alanı temizle
                            await username_input.fill('')
                            await asyncio.sleep(0.5)
                            
                            # Username'i yaz
                            await username_input.type(self.username, delay=100)
                            logging.info(f'⚡ Username entered: {self.username}')
                            await asyncio.sleep(2)
                            
                            # Enter tuşuna bas
                            await page.keyboard.press('Enter')
                            username_entered = True
                            break
                        else:
                            logging.warning(f"⚠️ Element bulundu ama görünür değil: {selector}")
                    
                except Exception as e:
                    logging.warning(f"⚠️ Selector {selector} başarısız: {e}")
                    continue
                    
            if not username_entered:
                logging.error("❌ Could not enter username - trying alternative method")
                
                # Alternatif yöntem: Tüm input'ları bul
                try:
                    inputs = await page.query_selector_all('input')
                    logging.info(f"🔍 Toplam {len(inputs)} input bulundu")
                    
                    for i, input_elem in enumerate(inputs):
                        try:
                            is_visible = await input_elem.is_visible()
                            input_type = await input_elem.get_attribute('type')
                            placeholder = await input_elem.get_attribute('placeholder')
                            
                            logging.info(f"Input {i}: visible={is_visible}, type={input_type}, placeholder={placeholder}")
                            
                            if is_visible and input_type != 'hidden':
                                await input_elem.click()
                                await asyncio.sleep(1)
                                await input_elem.fill(self.username)
                                await asyncio.sleep(1)
                                await page.keyboard.press('Enter')
                                username_entered = True
                                logging.info(f"✅ Username entered via alternative method")
                                break
                        except:
                            continue
                            
                except Exception as e:
                    logging.error(f"❌ Alternative method failed: {e}")
                    
            if not username_entered:
                logging.error("❌ Could not enter username with any method")
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
                    password_input = await page.wait_for_selector(selector, timeout=10000)
                    if password_input:
                        is_visible = await password_input.is_visible()
                        if is_visible:
                            await password_input.click()
                            await asyncio.sleep(1)
                            await password_input.fill(self.password)
                            logging.info('⚡ Password entered')
                            await asyncio.sleep(1)
                            await page.keyboard.press('Enter')
                            password_entered = True
                            break
                except Exception as e:
                    logging.warning(f"Password selector {selector} failed: {e}")
                    continue
                    
            if not password_entered:
                logging.error("❌ Could not enter password")
                return False
                
            await asyncio.sleep(8)  # Login sonrası daha uzun bekle
            
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
                logging.info('📧 Email doğrulama gerekiyor - otomatik işlem başlatılıyor...')
                return await self.manual_verification_input(page)
            
            return await self.check_login_success(page)
            
        except Exception as e:
            logging.error(f"❌ Login error: {e}")
            return False
            
    async def login(self):
        if await self.quick_login_check():
            return True
        return await self.direct_login()
        
    async def post_thread(self, thread_content):
        """DÜZELTME: Thread'i tek seferde gönder"""
        try:
            # TİP KONTROLÜ - ÇOK ÖNEMLİ!
            if isinstance(thread_content, list):
                tweets = thread_content
            elif isinstance(thread_content, str):
                # String'i cümlelere böl
                tweets = self.content_generator.split_content_by_sentences(thread_content, char_limit=270)
            else:
                logging.error(f"❌ İçerik tipi desteklenmiyor: {type(thread_content)}")
                return False
            
            logging.info(f"📝 Thread gönderiliyor: {len(tweets)} tweet")

            # 1. Compose sayfasını aç
            await self.page.goto("https://x.com/compose/tweet", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            for i, tweet_text in enumerate(tweets):
                # Tweet alanını bul
                compose_element = None
                for selector in [
                    "div[data-testid='tweetTextarea_0']",
                    "div[contenteditable='true'][data-testid='tweetTextarea_0']",
                    "div[role='textbox'][data-testid='tweetTextarea_0']",
                    "div[contenteditable='true']",
                    "div[role='textbox']"
                ]:
                    try:
                        compose_element = await self.page.wait_for_selector(selector, timeout=10000)
                        if compose_element:
                            break
                    except Exception as e:
                        logging.warning(f"⚠️ Tweet alanı seçici hatası: {e}")
                        continue

                if not compose_element:
                    logging.error("❌ Tweet yazma alanı bulunamadı!")
                    return False

                # Alanı temizle ve tweeti yaz
                await compose_element.click()
                await asyncio.sleep(1)
                await compose_element.fill(tweet_text)
                await asyncio.sleep(1)

                # Son tweet değilse + butonuna tıkla
                if i < len(tweets) - 1:
                    plus_button = None
                    for plus_selector in [
                        "button[data-testid='addButton']",
                        "div[aria-label='Add post']",
                        "[role='button'][aria-label='Add post']",
                        "button[aria-label='Add post']"
                    ]:
                        try:
                            plus_button = await self.page.wait_for_selector(plus_selector, timeout=5000)
                            if plus_button:
                                await plus_button.click()
                                await asyncio.sleep(2)  # Daha uzun bekleme süresi ekle
                                logging.info(f"✅ Tweet {i+1} eklendi, + butonuna tıklandı")
                                break
                        except Exception as e:
                            logging.warning(f"⚠️ + butonu seçici hatası: {e}")
                            continue
                    if not plus_button:
                        logging.error("❌ + butonu bulunamadı!")
                        return False

            # Son tweetten sonra gönder butonuna tıkla
            post_button = None
            for post_selector in [
                "div[data-testid='tweetButton']",
                "div[data-testid='tweetButtonInline']",
                "button[data-testid='tweetButton']",
                "[role='button'][data-testid='tweetButton']"
            ]:
                try:
                    post_button = await self.page.wait_for_selector(post_selector, timeout=10000)
                    if post_button:
                        await post_button.click()
                        await asyncio.sleep(5)
                        logging.info("✅ Thread zincir olarak gönderildi!")
                        return True
                except Exception as e:
                    logging.warning(f"⚠️ Gönder butonu seçici hatası: {e}")
                    continue

            logging.error("❌ Thread gönderilemedi!")
            return False

        except Exception as e:
            logging.error(f"❌ Thread gönderme hatası: {e}")
            return False

    async def reply_to_tweet(self, tweet_id, reply_content):
        """DÜZELTME: Tweet'e yanıt ver"""
        try:
            logging.info(f"💬 Tweet'e yanıt hazırlanıyor - Tweet ID: {tweet_id}")
            logging.info(f"💬 Yanıt içeriği: {reply_content}")
            
            # Tweet sayfasına git
            await self.page.goto(f"https://x.com/i/web/status/{tweet_id}", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)
            
            # Reply butonuna tıkla
            reply_selectors = [
                '[data-testid="reply"]',
                'div[data-testid="reply"]',
                'button[data-testid="reply"]'
            ]
            
            reply_clicked = False
            for selector in reply_selectors:
                try:
                    reply_button = await self.page.wait_for_selector(selector, timeout=5000)
                    if reply_button:
                        await reply_button.click()
                        await asyncio.sleep(3)
                        reply_clicked = True
                        logging.info("✅ Reply butonu tıklandı")
                        break
                except:
                    continue
            
            if not reply_clicked:
                logging.error("❌ Reply butonu bulunamadı")
                return False
            
            # Reply alanını bul ve doldur
            reply_area_selectors = [
                'div[data-testid="tweetTextarea_0"]',
                'div[contenteditable="true"]',
                'div[role="textbox"]'
            ]
            
            reply_area = None
            for selector in reply_area_selectors:
                try:
                    reply_area = await self.page.wait_for_selector(selector, timeout=5000)
                    if reply_area:
                        logging.info(f"✅ Reply alanı bulundu: {selector}")
                        break
                except:
                    continue
            
            if not reply_area:
                logging.error("❌ Reply alanı bulunamadı")
                return False
            
            # Reply içeriğini yaz
            await reply_area.click()
            await asyncio.sleep(1)
            await reply_area.fill(reply_content)
            await asyncio.sleep(2)
            
            # Reply gönder
            reply_post_selectors = [
                '[data-testid="tweetButton"]',
                'div[data-testid="tweetButtonInline"]',
                'button[data-testid="tweetButton"]'
            ]
            
            for selector in reply_post_selectors:
                try:
                    post_button = await self.page.wait_for_selector(selector, timeout=5000)
                    if post_button:
                        await post_button.click()
                        await asyncio.sleep(3)
                        logging.info("✅ Reply gönderildi")
                        return True
                except:
                    continue
            
            # Klavye kısayolu dene
            await self.page.keyboard.press('Ctrl+Enter')
            await asyncio.sleep(3)
            logging.info("✅ Reply klavye kısayolu ile gönderildi")
            return True
            
        except Exception as e:
            logging.error(f"❌ Reply gönderme hatası: {e}")
            return False

    async def get_latest_tweet_id(self, username):
        """DÜZELTME: Kullanıcının son tweet ID'sini al"""
        try:
            logging.info(f"🔍 Getting latest tweet for @{username}")
        
            # Kullanıcı profiline git - timeout'u artır
            await self.page.goto(f"https://x.com/{username}", wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(8)  # Daha uzun bekle
        
            # Sayfanın tam yüklenmesini bekle
            try:
                await self.page.wait_for_selector('[data-testid="primaryColumn"]', timeout=15000)
                logging.info("✅ Primary column yüklendi")
            except:
                logging.warning("⚠️ Primary column yüklenemedi, devam ediliyor...")
        
            # Tweet elementlerini bul - birden fazla yöntem
            tweet_found = False
            tweet_id = None
        
            # Yöntem 1: Article elementleri
            try:
                articles = await self.page.query_selector_all('article[data-testid="tweet"]')
                logging.info(f"🔍 {len(articles)} article bulundu")
                
                if articles and len(articles) > 0:
                    for i, article in enumerate(articles[:3]):  # İlk 3 tweet'i kontrol et
                        try:
                            tweet_link = await article.query_selector('a[href*="/status/"]')
                            if tweet_link:
                                href = await tweet_link.get_attribute('href')
                                if href and '/status/' in href:
                                    tweet_id = href.split('/status/')[1].split('/')[0].split('?')[0]
                                    if tweet_id and tweet_id.isdigit():
                                        logging.info(f"✅ Tweet ID bulundu (Article {i}): {tweet_id}")
                                        tweet_found = True
                                        break
                        except Exception as e:
                            logging.warning(f"⚠️ Article {i} işlenirken hata: {e}")
                            continue
            except Exception as e:
                logging.warning(f"Article yöntemi başarısız: {e}")
        
            # Yöntem 2: Direct link selectors
            if not tweet_found:
                try:
                    link_selectors = [
                        'a[href*="/status/"]',
                        '[data-testid="tweet"] a[href*="/status/"]',
                        'article a[href*="/status/"]'
                    ]
                
                    for selector in link_selectors:
                        try:
                            links = await self.page.query_selector_all(selector)
                            logging.info(f"🔍 {selector}: {len(links)} link bulundu")
                            
                            if links:
                                for j, link in enumerate(links[:5]):  # İlk 5 linki kontrol et
                                    href = await link.get_attribute('href')
                                    if href and '/status/' in href and f'/{username}/' in href:
                                        tweet_id = href.split('/status/')[1].split('/')[0].split('?')[0]
                                        if tweet_id and tweet_id.isdigit():
                                            logging.info(f"✅ Tweet ID bulundu (Link {j}): {tweet_id}")
                                            tweet_found = True
                                            break
                                if tweet_found:
                                    break
                        except Exception as e:
                            logging.warning(f"⚠️ Selector {selector} başarısız: {e}")
                            continue
                except Exception as e:
                    logging.warning(f"Link yöntemi başarısız: {e}")
        
            # Yöntem 3: Time elements
            if not tweet_found:
                try:
                    time_elements = await self.page.query_selector_all('time')
                    logging.info(f"🔍 {len(time_elements)} time element bulundu")
                    
                    for k, time_elem in enumerate(time_elements[:3]):
                        try:
                            # Parent link'i bul
                            parent_article = await time_elem.query_selector('xpath=ancestor::article')
                            if parent_article:
                                tweet_link = await parent_article.query_selector('a[href*="/status/"]')
                                if tweet_link:
                                    href = await tweet_link.get_attribute('href')
                                    if href and '/status/' in href:
                                        tweet_id = href.split('/status/')[1].split('/')[0].split('?')[0]
                                        if tweet_id and tweet_id.isdigit():
                                            logging.info(f"✅ Tweet ID bulundu (Time {k}): {tweet_id}")
                                            tweet_found = True
                                            break
                        except Exception as e:
                            logging.warning(f"⚠️ Time element {k} işlenirken hata: {e}")
                            continue
                except Exception as e:
                    logging.warning(f"Time yöntemi başarısız: {e}")
        
            if tweet_found and tweet_id:
                logging.info(f"✅ @{username} için tweet ID: {tweet_id}")
                return tweet_id
            else:
                logging.warning(f"⚠️ @{username} için tweet bulunamadı")
                return None
            
        except Exception as e:
            logging.error(f"❌ @{username} için tweet ID alma hatası: {e}")
            return None

    async def get_tweet_content(self, tweet_id):
        """Tweet içeriğini al - İYİLEŞTİRİLMİŞ"""
        try:
            logging.info(f"📄 Getting content for tweet: {tweet_id}")
        
            await self.page.goto(f"https://x.com/i/web/status/{tweet_id}", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
        
            # Tweet içeriğini bul - birden fazla yöntem
            content = None
        
            # Yöntem 1: Standard tweet text selector
            content_selectors = [
                '[data-testid="tweetText"]',
                'div[data-testid="tweetText"]',
                'article[data-testid="tweet"] [data-testid="tweetText"]'
            ]
        
            for selector in content_selectors:
                try:
                    content_element = await self.page.wait_for_selector(selector, timeout=8000)
                    if content_element:
                        content = await content_element.inner_text()
                        if content and content.strip():
                            logging.info(f"✅ Tweet içeriği bulundu: {content[:100]}...")
                            return content.strip()
                except:
                    continue
        
            # Yöntem 2: Lang attribute ile
            try:
                lang_elements = await self.page.query_selector_all('div[lang]')
                for elem in lang_elements:
                    text = await elem.inner_text()
                    if text and len(text) > 10:  # Minimum content length
                        content = text.strip()
                        logging.info(f"✅ Tweet içeriği bulundu (lang): {content[:100]}...")
                        return content
            except:
                pass
        
            # Yöntem 3: Article içindeki text
            try:
                article = await self.page.query_selector('article[data-testid="tweet"]')
                if article:
                    text_content = await article.inner_text()
                    # Tweet text'ini ayıkla (username, time vs. hariç)
                    lines = text_content.split('\n')
                    for line in lines:
                        if len(line) > 20 and not line.startswith('@') and not 'ago' in line:
                            content = line.strip()
                            logging.info(f"✅ Tweet içeriği bulundu (article): {content[:100]}...")
                            return content
            except:
                pass
        
            logging.warning(f"⚠️ Tweet içeriği bulunamadı: {tweet_id}")
            return None
            
        except Exception as e:
            logging.error(f"❌ Tweet içeriği alma hatası: {e}")
            return None

    async def get_tweet_time(self, tweet_id):
        """Tweet'in atılma zamanını al - İYİLEŞTİRİLMİŞ"""
        try:
            logging.info(f"🕐 Getting time for tweet: {tweet_id}")
        
            # Zaten tweet sayfasındaysak tekrar gitmeye gerek yok
            current_url = self.page.url
            if f"/status/{tweet_id}" not in current_url:
                await self.page.goto(f"https://x.com/i/web/status/{tweet_id}", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
        
            # Zaman damgası elementini bul
            time_selectors = [
                'time[datetime]',
                'article time[datetime]',
                '[data-testid="tweet"] time'
            ]
        
            for selector in time_selectors:
                try:
                    time_element = await self.page.wait_for_selector(selector, timeout=8000)
                    if time_element:
                        datetime_str = await time_element.get_attribute('datetime')
                        if datetime_str:
                            tweet_time = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                            logging.info(f"✅ Tweet zamanı: {tweet_time}")
                            return tweet_time
                except:
                    continue
        
            # Alternatif: Relative time'dan çıkarım yap
            try:
                time_elements = await self.page.query_selector_all('time')
                for time_elem in time_elements:
                    time_text = await time_elem.inner_text()
                    if 'h' in time_text or 'm' in time_text or 's' in time_text:
                        # Yaklaşık zaman hesapla
                        now = datetime.now()
                        if 'h' in time_text:
                            hours = int(time_text.replace('h', '').strip())
                            tweet_time = now - timedelta(hours=hours)
                        elif 'm' in time_text:
                            minutes = int(time_text.replace('m', '').strip())
                            tweet_time = now - timedelta(minutes=minutes)
                        else:
                            tweet_time = now  # Very recent
                    
                        logging.info(f"✅ Tweet zamanı (yaklaşık): {tweet_time}")
                        return tweet_time
            except:
                pass
        
            logging.warning(f"⚠️ Tweet zamanı bulunamadı: {tweet_id}")
            # Varsayılan olarak şu anki zamanı döndür (1 saat içinde sayılsın)
            return datetime.now()
            
        except Exception as e:
            logging.error(f"❌ Tweet zamanı alma hatası: {e}")
            return datetime.now()

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

    # Email bilgilerini kontrol et - birden fazla seçenek dene
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS') or os.getenv('EMAIL_USER')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD') or os.getenv('GMAIL_APP_PASSWORD') or os.getenv('EMAIL_PASS')
    
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        logging.error("❌ Gmail bilgileri environment variables'da eksik!")
        logging.error(f"   EMAIL_ADDRESS: {EMAIL_ADDRESS}")
        logging.error(f"   EMAIL_PASSWORD: {'Set' if EMAIL_PASSWORD else 'Not set'}")
        print("❌ Gmail bilgileri environment variables'da eksik!")
        return
        
    if not os.getenv('GEMINI_API_KEY'):
        logging.error("❌ Gemini API anahtarı environment variables'da eksik!")
        print("❌ Gemini API anahtarı environment variables'da eksik!")
        return

    # Sınıfları başlat
    email_handler = EmailHandler()
    content_generator = AdvancedContentGenerator()
    if not await content_generator.initialize():
        print("❌ Gemini başlatılamadı!")
        return
    twitter = TwitterBrowser(TWITTER_USERNAME, TWITTER_PASSWORD, email_handler, content_generator)
    await twitter.initialize()
    if not await twitter.login():
        print("❌ Twitter login başarısız!")
        return

    # Proje ve izlenen hesapları yükle
    projects = content_generator.projects
    accounts = content_generator.monitored_accounts

    logging.info("✅ Bot başlatıldı ve login oldu. Döngü başlıyor...")
    print("✅ Bot başlatıldı ve login oldu. Döngü başlıyor...")

    while True:
        try:
            # 1. Proje içerik üret ve tweet at
            selected_projects = random.sample(content_generator.projects, 2)
            
            for project in selected_projects:
                content = await content_generator.generate_project_content(project)
                if content and isinstance(content, str):  # STRING KONTROLÜ
                    logging.info(f"📝 Tweet paylaşılacak içerik: {content}")
                    await twitter.post_thread(content)
                    await asyncio.sleep(random.uniform(30, 60))  # İki tweet arası bekle
                else:
                    logging.warning("⚠️ İçerik üretilemedi veya string değil, tweet atlanıyor.")

            # 2. İzlenen hesapların son tweetlerine reply at
            reply_count = 0
            max_replies_per_cycle = 3  # Döngü başına maksimum reply sayısı (azalttık)

            for account in accounts[:8]:  # İlk 8 hesabı kontrol et (azalttık)
                try:
                    if reply_count >= max_replies_per_cycle:
                        logging.info(f"✅ Maksimum reply sayısına ulaşıldı ({max_replies_per_cycle})")
                        break
                        
                    logging.info(f"🔍 {account} hesabı kontrol ediliyor...")
                    
                    tweet_id = await twitter.get_latest_tweet_id(account)
                    if tweet_id:
                        logging.info(f"✅ Tweet ID bulundu: {tweet_id}")
                        
                        tweet_content = await twitter.get_tweet_content(tweet_id)
                        if tweet_content:
                            logging.info(f"✅ Tweet içeriği alındı: {tweet_content[:100]}...")
                            
                            # Son 1 saatin tweet'i mi kontrol et
                            tweet_time = await twitter.get_tweet_time(tweet_id)
                            if tweet_time:
                                time_diff = (datetime.now() - tweet_time).total_seconds()
                                logging.info(f"⏰ Tweet yaşı: {time_diff/3600:.1f} saat")
                                
                                if time_diff <= 3600:  # 1 saat = 3600 saniye
                                    logging.info(f"✅ Tweet son 1 saat içinde, reply üretiliyor...")
                                    
                                    reply = await content_generator.generate_reply({'text': tweet_content, 'username': account})
                                    if reply and isinstance(reply, str):  # STRING KONTROLÜ
                                        logging.info(f"💬 Reply üretildi: {reply}")
                                        
                                        # Reply'ı gönder
                                        if await twitter.reply_to_tweet(tweet_id, reply):
                                            reply_count += 1
                                            logging.info(f"✅ Reply gönderildi! ({reply_count}/{max_replies_per_cycle})")
                                            await asyncio.sleep(random.uniform(60, 120))  # Reply arası daha uzun bekle
                                        else:
                                            logging.error("❌ Reply gönderilemedi")
                                    else:
                                        logging.warning("⚠️ Reply üretilemedi veya string değil")
                                else:
                                    logging.info(f"ℹ️ Tweet çok eski ({time_diff/3600:.1f} saat), atlanıyor")
                            else:
                                logging.warning("⚠️ Tweet zamanı alınamadı")
                        else:
                            logging.warning("⚠️ Tweet içeriği alınamadı")
                    else:
                        logging.warning(f"⚠️ {account} için tweet bulunamadı")
                        
                except Exception as e:
                    logging.error(f"❌ {account} için reply hatası: {e}")
                    continue

            logging.info(f"✅ Reply döngüsü tamamlandı. Toplam reply: {reply_count}")

            logging.info("⏳ 2 saat bekleniyor...")
            print("⏳ 2 saat bekleniyor...")
            await asyncio.sleep(2 * 60 * 60)  # 2 saat bekle
        except Exception as e:
            logging.error(f"❌ Ana döngü hatası: {e}")
            print(f"❌ Ana döngü hatası: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
