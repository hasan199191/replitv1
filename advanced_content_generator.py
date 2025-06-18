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
from playwright_stealth import stealth
import imaplib
import email
from advanced_content_generator import AdvancedContentGenerator  # <-- Yeni import

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

class ContentGenerator:
    def __init__(self):
        self.model = None
        
    def initialize(self):
        try:
            gemini_api_key = os.getenv('GEMINI_API_KEY')
            if not gemini_api_key:
                logging.error("Error initializing Gemini Flash 2.0: Gemini API key not found")
                return False
                
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            
            logging.info("Advanced Gemini Flash 2.0 successfully initialized")
            return True
            
        except Exception as e:
            logging.error(f"Error initializing Gemini: {e}")
            return False
            
    def generate_project_content(self, projects):
        """2 rastgele proje için temiz İngilizce içerik oluştur"""
        try:
            if not projects or len(projects) < 2:
                logging.error("Projeler listesi 2'den az! İçerik üretilemiyor.")
                return None, None
            selected_projects = random.sample(projects, 2)
            
            prompt = f"""
Create engaging English Twitter content about these 2 crypto projects:

1. {selected_projects[0]['name']} ({selected_projects[0]['twitter']})
   - Category: {selected_projects[0]['category']}
   - Website: {selected_projects[0]['website']}

2. {selected_projects[1]['name']} ({selected_projects[1]['twitter']})
   - Category: {selected_projects[1]['category']}
   - Website: {selected_projects[1]['website']}

IMPORTANT RULES:
- Write ONLY in English
- NO prefixes like "Tweet 1:", "Tweet 2:" etc.
- Use plain text only, no special characters
- Start content directly about the projects
- Tag both projects properly with their handles
- Each sentence must be complete
- Be informative and engaging
- Use hashtags: #DeFi #Web3 #Crypto #Blockchain
- Sound natural, not robotic
- Maximum total content around 500 characters

Create the content:
"""
            
            response = self.model.generate_content(prompt)
            content = response.text.strip()
            
            # Clean all unwanted prefixes and special characters
            content = content.replace('**', '').replace('##', '').replace('***', '')
            content = content.replace('Tweet 1:', '').replace('Tweet 2:', '').replace('Tweet 3:', '')
            content = content.replace('TWEET1:', '').replace('TWEET2:', '').replace('TWEET3:', '')
            content = content.strip()
            
            # Remove multiple newlines and clean up
            import re
            content = re.sub(r'\n\s*\n', ' ', content)
            content = re.sub(r'\s+', ' ', content)
            
            return content, selected_projects
            
        except Exception as e:
            logging.error(f"Error generating project content: {e}")
            return None, None
            
    def generate_reply_content(self, tweet_content, author):
        """Tweet'e İngilizce cevap için içerik oluştur"""
        try:
            prompt = f"""
Create a smart, valuable English reply to this tweet:

Tweet: "{tweet_content}"
Author: @{author}

Rules:
- Write ONLY in English
- Maximum 200 characters
- No special characters (**, ##, etc.)
- Don't sound like spam
- Provide valuable insight
- Be genuine and professional
- Don't sound like a bot
- Use 1-2 emojis max
- Be concise and relevant
- Add value to the conversation

Only provide the reply text:
"""
            
            response = self.model.generate_content(prompt)
            reply = response.text.strip()
            
            # Clean special characters
            reply = reply.replace('**', '').replace('##', '').replace('***', '')
            reply = reply.replace('"', '').replace("'", "'")
            
            return reply
            
        except Exception as e:
            logging.error(f"Error generating reply: {e}")
            return None
            
    def split_content_by_sentences(self, content, char_limit=250):
        """İçeriği cümle bazında böl"""
        try:
            # Single paragraph
            content = content.replace('\n', ' ').strip()
            
            # Split by sentences
            import re
            sentences = re.split(r'(?<=[.!?])\s+', content)
            
            tweets = []
            current_tweet = ""
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                # Can we add this sentence?
                test_tweet = current_tweet + (" " if current_tweet else "") + sentence
                
                if len(test_tweet) <= char_limit:
                    current_tweet = test_tweet
                else:
                    # Save current tweet
                    if current_tweet:
                        tweets.append(current_tweet.strip())
                    # Start new tweet
                    current_tweet = sentence
            
            # Add last tweet
            if current_tweet:
                tweets.append(current_tweet.strip())
            
            return tweets
            
        except Exception as e:
            logging.error(f"Error splitting content: {e}")
            return [content[:char_limit]]

class TwitterBrowser:
    def __init__(self, username, password, email_handler=None, content_generator=None):
        self.username = username
        self.password = password
        self.email_handler = email_handler
        self.content_generator = content_generator
        self.playwright = None
        self.context = None
        self.page = None
        self.user_data_dir = "pw_profile"

    async def initialize(self):
        try:
            self.playwright = await async_playwright().start()
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,  # Render için True olabilir
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
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
            # Stealth fonksiyonunu doğru şekilde çağır
            if callable(stealth):
                await stealth(self.page)
            else:
                logging.warning("playwright_stealth.stealth fonksiyonu bulunamadı veya çağrılamıyor!")
            await self.page.goto("https://x.com/home", wait_until="networkidle")
            await asyncio.sleep(5)
            logging.info("✅ Chrome initialized with persistent profile!")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to initialize Chrome: {e}")
            return False

    async def check_login_success(self, page):
        try:
            await asyncio.sleep(3)
            current_url = page.url.lower()
            
            if 'login' not in current_url and 'signin' not in current_url and 'flow' not in current_url:
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
            for _ in range(2):  # 2 kez dene
                try:
                    await self.page.goto('https://x.com/home', wait_until='networkidle', timeout=20000)
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
            
            await page.goto('https://x.com/i/flow/login', wait_until='networkidle')
            await asyncio.sleep(5)
            
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
                
                logging.info(f"📧 Email Handler durumu:")
                logging.info(f"   - Email: {self.email_handler.email}")
                logging.info(f"   - Password: {'✅ Set' if self.email_handler.password else '❌ Not set'}")
                logging.info(f"   - Password length: {len(self.email_handler.password) if self.email_handler.password else 0}")
                
                if self.email_handler and self.email_handler.email and self.email_handler.password:
                    logging.info("🔄 Gmail'den kod alınıyor...")
                    
                    code = await self.email_handler.get_verification_code(timeout=90)
                    
                    if code:
                        logging.info(f'✅ Gmail\'den kod alındı: {code}')
                        
                        try:
                            code_input = page.locator('input[data-testid="ocfEnterTextTextInput"]')
                            await code_input.fill(str(code))
                            await asyncio.sleep(1)
                            await page.keyboard.press('Enter')
                            await asyncio.sleep(3)
                            
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
            
            return await self.check_login_success(page)
            
        except Exception as e:
            logging.error(f"❌ Login error: {e}")
            return False
            
    async def login(self):
        if await self.quick_login_check():
            return True
        return await self.direct_login()
        
    async def post_thread(self, thread_content):
        """Thread olarak gönder - + butonu kullanarak"""
        try:
            logging.info("📝 İçerik hazırlanıyor...")
            logging.info(f"📝 Ham içerik: {thread_content[:200]}...")

            # Tweet compose sayfasına git ve sayfanın tam yüklenmesini bekle
            try:
                await self.page.goto("https://x.com/compose/tweet", wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(5)  # Sayfanın tam yüklenmesi için bekle
            except Exception as e:
                logging.warning(f"Compose sayfası yüklenemedi, ana sayfadan deneniyor: {e}")
                await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(5)
                
                tweet_button_selectors = [
                    '[data-testid="SideNav_NewTweet_Button"]',
                    '[href="/compose/post"]',
                    'a[aria-label*="Post"]',
                    'button[aria-label*="Post"]',
                    '[data-testid="tweetButtonInline"]'
                ]
                for selector in tweet_button_selectors:
                    try:
                        tweet_btn = await self.page.wait_for_selector(selector, timeout=5000)
                        if tweet_btn:
                            await tweet_btn.click()
                            await asyncio.sleep(3)
                            break
                    except:
                        continue

            # Tweet compose alanını bulmak için birkaç kez dene
            compose_element = None
            max_retries = 3
            for attempt in range(max_retries):
                compose_selectors = [
                    'div[data-testid="tweetTextarea_0"]',
                    'div[contenteditable="true"][data-testid="tweetTextarea_0"]',
                    'div[role="textbox"][data-testid="tweetTextarea_0"]',
                    'div[contenteditable="true"]',
                    'div[role="textbox"]',
                    'div[aria-label*="Tweet text"]',
                    'div[aria-label="Text editor"]'
                ]
                
                for selector in compose_selectors:
                    try:
                        compose_element = await self.page.wait_for_selector(selector, timeout=10000)
                        if compose_element:
                            logging.info(f"✅ Tweet compose alanı bulundu: {selector}")
                            # İçeriği yazmayı dene
                            await compose_element.click()
                            await asyncio.sleep(2)
                            await compose_element.fill(thread_content)
                            await asyncio.sleep(2)
                            
                            # İçeriğin yazılıp yazılmadığını kontrol et
                            element_text = await compose_element.text_content()
                            if element_text:
                                logging.info("✅ Tweet içeriği başarıyla yazıldı")
                                break
                            else:
                                logging.warning("⚠️ İçerik yazılamadı, alternatif yöntem deneniyor...")
                                # Alternatif yazma yöntemi
                                await compose_element.click()
                                await asyncio.sleep(1)
                                await self.page.keyboard.press("Control+A")
                                await asyncio.sleep(1)
                                await self.page.keyboard.press("Backspace")
                                await asyncio.sleep(1)
                                await self.page.keyboard.type(thread_content, delay=100)
                                await asyncio.sleep(2)
                    except Exception as e:
                        logging.warning(f"Selector {selector} ile içerik yazılamadı: {e}")
                        continue

                if compose_element and await compose_element.text_content():
                    break
                
                if attempt < max_retries - 1:
                    logging.warning(f"İçerik yazma denemesi {attempt + 1} başarısız, tekrar deneniyor...")
                    await asyncio.sleep(3)

            if not compose_element or not await compose_element.text_content():
                logging.error("❌ Tweet içeriği yazılamadı!")
                return False

            # Tweet gönder butonunu bul ve tıkla
            post_button = None
            post_selectors = [
                '[data-testid="tweetButton"]',
                'div[data-testid="tweetButtonInline"]',
                'button[data-testid="tweetButton"]',
                '[role="button"][data-testid="tweetButton"]',
                'div[data-testid="toolBar"] [role="button"]:has-text("Post")',
                'div[data-testid="toolBar"] [role="button"]:has-text("Tweet")'
            ]

            for selector in post_selectors:
                try:
                    post_button = await self.page.wait_for_selector(selector, timeout=10000)
                    if post_button:
                        is_disabled = await post_button.get_attribute('aria-disabled')
                        if is_disabled != 'true':
                            logging.info(f"✅ Tweet gönder butonu bulundu: {selector}")
                            await post_button.click()
                            await asyncio.sleep(5)
                            logging.info("✅ Tweet gönderildi!")
                            return True
                except Exception as e:
                    logging.warning(f"Gönder butonu {selector} tıklanamadı: {e}")
                    continue

            logging.error("❌ Tweet gönderilemedi!")
            return False

        except Exception as e:
            logging.error(f"❌ Thread gönderme hatası: {e}")
            return False

    async def reply_to_tweet(self, tweet_id, reply_content):
        """Bir tweete yanıt gönder"""
        try:
            logging.info(f"💬 Tweet'e yanıt hazırlanıyor - Tweet ID: {tweet_id}")
            logging.info(f"💬 Yanıt içeriği: {reply_content}")
            
            # Yanıtı 2 parçaya böl
            reply_parts = self.content_generator.split_content_by_sentences(reply_content, char_limit=200)
            
            logging.info(f"💬 Toplam {len(reply_parts)} yanıt parçası tespit edildi")
            
            for i, part in enumerate(reply_parts):
                try:
                    logging.info(f"🚀 Yanıt parçası gönderiliyor ({i+1}/{len(reply_parts)}): {part}")
                    
                    await self.page.goto(f"https://x.com/i/web/status/{tweet_id}", wait_until="networkidle")
                    await asyncio.sleep(5)
                    
                    # Yanıt metnini bul ve doldur
                    reply_selectors = [
                        'div[aria-labelledby^="editable-"]',  # Yeni yanıt düzenleyici
                        'div[role="textbox"]'  # Eski yanıt düzenleyici
                    ]
                    
                    reply_input = None
                    for selector in reply_selectors:
                        try:
                            reply_input = self.page.locator(selector)
                            if await reply_input.count() > 0:
                                logging.info(f"✅ Yanıt girişi için element bulundu: {selector}")
                                break
                        except:
                            continue
                    
                    if reply_input is None:
                        logging.error("❌ Yanıt girişi için uygun element bulunamadı")
                        return False
                    
                    await reply_input.fill(part)
                    await asyncio.sleep(2)
                    
                    # Gönder butonuna tıkla
                    await self.page.locator('div[data-testid="tweetButtonInline"]').click()
                    logging.info("✅ Yanıt gönderildi")
                    
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logging.error(f"❌ Yanıt gönderme hatası: {e}")
                    return False
            
            logging.info("✅ Tüm yanıt parçaları başarıyla gönderildi")
            return True
            
        except Exception as e:
            logging.error(f"❌ Yanıt gönderme hatası: {e}")
            return False

    async def get_latest_tweet_id(self, username):
        """Bir kullanıcının son tweet ID'sini al"""
        try:
            await self.page.goto(f"https://x.com/{username}", wait_until="networkidle", timeout=20000)
            await asyncio.sleep(3)

            # Tweet elementini bul
            tweet_selectors = [
                'article[data-testid="tweet"]',
                'div[data-testid="tweet"]',
                '[data-testid="tweetText"]'
            ]
            
            for selector in tweet_selectors:
                try:
                    tweets = await self.page.query_selector_all(selector)
                    if tweets and len(tweets) > 0:
                        # İlk tweet'in ID'sini al
                        tweet_link = await tweets[0].query_selector('a[href*="/status/"]')
                        if tweet_link:
                            href = await tweet_link.get_attribute('href')
                            tweet_id = href.split('/status/')[1].split('/')[0]
                            return tweet_id
                except Exception as e:
                    logging.warning(f"Tweet selector {selector} failed: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting latest tweet ID: {e}")
            return None

    async def get_tweet_content(self, tweet_id):
        """Tweet içeriğini al"""
        try:
            await self.page.goto(f"https://x.com/i/web/status/{tweet_id}", wait_until="networkidle", timeout=20000)
            await asyncio.sleep(2)
            
            # Tweet içeriğini bul
            content_selectors = [
                '[data-testid="tweetText"]',
                'article[data-testid="tweet"] div[lang]',
                'div[data-testid="tweetText"]'
            ]
            
            for selector in content_selectors:
                try:
                    content_element = await self.page.wait_for_selector(selector, timeout=5000)
                    if content_element:
                        content = await content_element.inner_text()
                        return content.strip()
                except:
                    continue
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting tweet content: {e}")
            return None

    async def get_tweet_time(self, tweet_id):
        """Tweet'in atılma zamanını al"""
        try:
            await self.page.goto(f"https://x.com/i/web/status/{tweet_id}", wait_until="networkidle", timeout=20000)
            await asyncio.sleep(2)
            
            # Zaman damgası elementini bul
            time_selectors = [
                'time[datetime]',
                '[data-testid="tweet"] time'
            ]
            
            for selector in time_selectors:
                try:
                    time_element = await self.page.wait_for_selector(selector, timeout=5000)
                    if time_element:
                        datetime_str = await time_element.get_attribute('datetime')
                        return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                except:
                    continue
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting tweet time: {e}")
            return None

async def main():
    logging.info("🚀 Bot başlatılıyor...")
    print("🚀 Bot başlatılıyor...")

    # Gerekli environment değişkenlerini kontrol et
    TWITTER_USERNAME = os.getenv('TWITTER_USERNAME')
    TWITTER_PASSWORD = os.getenv('TWITTER_PASSWORD')
    if not TWITTER_USERNAME or not TWITTER_PASSWORD:
        logging.error("❌ Twitter kullanıcı adı veya şifre .env dosyasında eksik!")
        print("❌ Twitter kullanıcı adı veya şifre .env dosyasında eksik!")
        return

    # Email ve Gemini API anahtarlarını kontrol et
    if not os.getenv('EMAIL_ADDRESS') or not os.getenv('EMAIL_PASSWORD'):
        logging.error("❌ Gmail bilgileri .env dosyasında eksik!")
        print("❌ Gmail bilgileri .env dosyasında eksik!")
        return
    if not os.getenv('GEMINI_API_KEY'):
        logging.error("❌ Gemini API anahtarı .env dosyasında eksik!")
        print("❌ Gemini API anahtarı .env dosyasında eksik!")
        return

    # Sınıfları başlat
    email_handler = EmailHandler()
    content_generator = AdvancedContentGenerator()  # ContentGenerator yerine AdvancedContentGenerator kullan
    if not await content_generator.initialize():  # initialize async olduğu için await ekle
        print("❌ Gemini başlatılamadı!")
        return
    twitter = TwitterBrowser(TWITTER_USERNAME, TWITTER_PASSWORD, email_handler, content_generator)
    await twitter.initialize()
    if not await twitter.login():
        print("❌ Twitter login başarısız!")
        return

    # Proje ve izlenen hesapları load_data() ile yükle
    projects = content_generator.projects
    accounts = content_generator.monitored_accounts

    logging.info("✅ Bot başlatıldı ve login oldu. Döngü başlıyor...")
    print("✅ Bot başlatıldı ve login oldu. Döngü başlıyor...")

    while True:
        try:
            # 1. Proje içerik üret ve thread olarak tweetle
            selected_projects = random.sample(content_generator.projects, 2)
            content = await content_generator.generate_project_content(selected_projects[0])  # İlk proje için içerik üret
            if content:
                logging.info(f"📝 Thread olarak paylaşılacak içerik (1): {content}")
                await twitter.post_thread(content)
                await asyncio.sleep(random.uniform(30, 60))  # İki tweet arası bekle
                
                content = await content_generator.generate_project_content(selected_projects[1])  # İkinci proje için içerik üret
                if content:
                    logging.info(f"📝 Thread olarak paylaşılacak içerik (2): {content}")
                    await twitter.post_thread(content)
            else:
                logging.warning("⚠️ İçerik üretilemedi, thread atlanıyor.")

            # 2. İzlenen hesapların son tweetlerine reply at
            for account in accounts:
                try:
                    tweet_id = await twitter.get_latest_tweet_id(account)  # account artık string
                    if tweet_id:
                        tweet_content = await twitter.get_tweet_content(tweet_id)
                        if tweet_content:
                            # Son 1 saatin tweet'i mi kontrol et
                            tweet_time = await twitter.get_tweet_time(tweet_id)
                            if tweet_time and (datetime.now() - tweet_time).total_seconds() <= 3600:  # 1 saat = 3600 saniye
                                reply = await content_generator.generate_reply_content(tweet_content, account)
                                if reply:
                                    await twitter.reply_to_tweet(tweet_id, reply)
                                    await asyncio.sleep(random.uniform(30, 60))  # Her reply arasında bekle
                except Exception as e:
                    logging.error(f"❌ {account} için reply hatası: {e}")
                    continue

            logging.info("⏳ 2 saat bekleniyor...")
            print("⏳ 2 saat bekleniyor...")
            await asyncio.sleep(2 * 60 * 60)  # 2 saat bekle
        except Exception as e:
            logging.error(f"❌ Ana döngü hatası: {e}")
            print(f"❌ Ana döngü hatası: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
