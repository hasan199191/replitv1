import imaplib
import email
import re
import time
import logging
import os
from typing import Optional

class EmailHandler:
    def __init__(self):
        self.email_user = "hasanacikgoz91@gmail.com"
        # Gmail App Password - boşlukları kaldır
        raw_password = os.environ.get('GMAIL_APP_PASSWORD') or os.environ.get('EMAIL_PASS') or "Nuray1965+"
        self.email_pass = raw_password.replace(' ', '') if raw_password else None
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        self.logger = logging.getLogger('EmailHandler')
        self.setup_logging()
        
    def setup_logging(self):
        """Loglama ayarlarını yapılandır"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def get_twitter_verification_code(self, timeout=120) -> Optional[str]:
        """Twitter'dan gelen doğrulama kodunu email'den al - DÜZELTİLMİŞ SEARCH"""
        try:
            # Gmail App Password kontrolü
            if not self.email_pass:
                self.logger.error("❌ No Gmail password/app password available!")
                return None
            
            # App Password kullanıldığını belirt
            if len(self.email_pass) == 16 and self.email_pass.isalnum():
                self.logger.info("🔐 Using Gmail App Password for authentication")
            else:
                self.logger.warning("⚠️ Using regular password - App Password recommended!")
                self.logger.info("💡 Create App Password: https://support.google.com/accounts/answer/185833")

            self.logger.info("📧 Connecting to Gmail for verification code...")
        
            start_time = time.time()
        
            while time.time() - start_time < timeout:
                try:
                    # Gmail'e bağlan
                    mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
                    
                    # App Password ile login dene
                    try:
                        mail.login(self.email_user, self.email_pass)
                        self.logger.info("✅ Successfully connected to Gmail")
                    except imaplib.IMAP4.error as login_error:
                        error_msg = str(login_error)
                        if "Application-specific password required" in error_msg:
                            self.logger.error("❌ Gmail App Password required!")
                            self.logger.info("🔧 Setup instructions:")
                            self.logger.info("1. Go to https://myaccount.google.com/security")
                            self.logger.info("2. Enable 2-Step Verification")
                            self.logger.info("3. Generate App Password for 'Mail'")
                            self.logger.info("4. Set GMAIL_APP_PASSWORD environment variable")
                            return None
                        else:
                            self.logger.error(f"❌ Gmail login failed: {error_msg}")
                            return None
                    
                    mail.select('inbox')
                
                    # BASİT SEARCH - Son 50 email'i al
                    self.logger.info("🔍 Searching for recent emails...")
                    
                    # Önce tüm email'leri al (son 50)
                    result, data = mail.search(None, 'ALL')
                    
                    if data[0]:
                        email_ids = data[0].split()
                        
                        # Son 50 email'i kontrol et
                        recent_emails = email_ids[-50:] if len(email_ids) > 50 else email_ids
                        
                        self.logger.info(f"📧 Checking {len(recent_emails)} recent emails...")
                        
                        # En son email'leri kontrol et
                        for email_id in reversed(recent_emails):
                            try:
                                result, data = mail.fetch(email_id, '(RFC822)')
                            
                                if data[0]:
                                    email_message = email.message_from_bytes(data[0][1])
                                
                                    # Email konusunu kontrol et
                                    subject = email_message.get('Subject', '')
                                    sender = email_message.get('From', '')
                                    date = email_message.get('Date', '')
                                    
                                    # Twitter/X email'i mi kontrol et
                                    is_twitter_email = any(domain in sender.lower() for domain in ['twitter.com', 'x.com']) or \
                                                     any(keyword in subject.lower() for keyword in ['twitter', 'x confirmation', 'verification', 'confirm', 'code', 'verify', 'security', 'login'])
                                    
                                    if is_twitter_email:
                                        self.logger.info(f"📧 Found Twitter email from {sender}: {subject}")
                                    
                                        # Email içeriğini al
                                        body = self.get_email_body(email_message)
                                    
                                        if body:
                                            # Doğrulama kodunu bul
                                            verification_code = self.extract_verification_code(body)
                                        
                                            if verification_code:
                                                self.logger.info(f"✅ Found Twitter verification code: {verification_code}")
                                                mail.close()
                                                mail.logout()
                                                return verification_code
                            except Exception as email_error:
                                self.logger.warning(f"⚠️ Error processing email {email_id}: {email_error}")
                                continue
                
                    mail.close()
                    mail.logout()
                
                    # 15 saniye bekle ve tekrar dene
                    self.logger.info("⏳ No verification code found, waiting 15 seconds...")
                    time.sleep(15)
                
                except Exception as e:
                    self.logger.error(f"❌ Error checking email: {e}")
                    time.sleep(15)
                    continue
        
            self.logger.warning("⚠️ Timeout waiting for verification code")
            return None
        
        except Exception as e:
            self.logger.error(f"❌ Error in email handler: {e}")
            return None
    
    def get_email_body(self, email_message):
        """Email içeriğini al"""
        try:
            body = ""
            
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            return body
            
        except Exception as e:
            self.logger.error(f"❌ Error getting email body: {e}")
            return ""
    
    def extract_verification_code(self, email_body):
        """Email içeriğinden doğrulama kodunu çıkar - X FORMAT DESTEKLİ"""
        try:
            # X/Twitter'ın yeni formatları dahil
            patterns = [
                # X/Twitter spesifik formatlar
                r'Your X confirmation code is[:\s]*([a-zA-Z0-9]{8})',  # Your X confirmation code is 6saz54wc
                r'confirmation code is[:\s]*([a-zA-Z0-9]{8})',        # confirmation code is 6saz54wc
                r'single-use code[:\s]*([a-zA-Z0-9]{8})',             # single-use code 6saz54wc
                r'code[:\s]*([a-zA-Z0-9]{8})',                        # code 6saz54wc
                
                # Geleneksel formatlar
                r'verification code[:\s]*([0-9]{6})',                 # verification code: 123456
                r'confirmation code[:\s]*([0-9]{6})',                 # confirmation code: 123456
                r'security code[:\s]*([0-9]{6})',                     # security code: 123456
                r'login code[:\s]*([0-9]{6})',                        # login code: 123456
                r'code[:\s]*([0-9]{6})',                              # code: 123456
                r'confirm[:\s]*([0-9]{6})',                           # confirm: 123456
                r'verify[:\s]*([0-9]{6})',                            # verify: 123456
                
                # Farklı uzunluklar
                r'([0-9]{6})',                                        # sadece 6 haneli sayı
                r'([0-9]{4})',                                        # sadece 4 haneli sayı
                r'([0-9]{8})',                                        # sadece 8 haneli sayı
                r'([a-zA-Z0-9]{8})',                                  # 8 karakterli alfanumerik
                
                # HTML formatları
                r'<.*?>([a-zA-Z0-9]{8})<.*?>',                        # HTML tag içinde 8 karakter
                r'<.*?>([0-9]{6})<.*?>',                              # HTML tag içinde 6 haneli
                r'<.*?>([0-9]{4})<.*?>',                              # HTML tag içinde 4 haneli
                
                # Özel Twitter formatları
                r'Your Twitter confirmation code is[:\s]*([a-zA-Z0-9]{6,8})',
                r'Your verification code is[:\s]*([a-zA-Z0-9]{6,8})',
                r'Enter this code[:\s]*([a-zA-Z0-9]{6,8})',
            ]
        
            email_lower = email_body.lower()
            original_body = email_body  # Orijinal case'i korumak için
        
            # Önce X/Twitter spesifik pattern'lerini dene
            x_patterns = [
                r'your x confirmation code is[:\s]*([a-zA-Z0-9]{8})',
                r'confirmation code is[:\s]*([a-zA-Z0-9]{8})',
                r'single-use code[:\s]*([a-zA-Z0-9]{8})',
            ]
        
            for pattern in x_patterns:
                matches = re.findall(pattern, email_lower, re.IGNORECASE)
                if matches:
                    code = matches[0]
                    if len(code) in [6, 8]:
                        self.logger.info(f"✅ Found X/Twitter code with pattern: {pattern}")
                        return code
        
            # Orijinal body'de de ara (case sensitive)
            for pattern in patterns:
                matches = re.findall(pattern, original_body, re.IGNORECASE)
            
                if matches:
                    # En uygun kodu seç
                    for code in matches:
                        if len(code) in [4, 6, 8]:
                            # Alfanumerik kodları tercih et (X'in yeni formatı)
                            if re.match(r'^[a-zA-Z0-9]+$', code):
                                self.logger.info(f"✅ Found code with pattern: {pattern}")
                                return code
        
            # Son çare: email body'de tüm alfanumerik kodları bul
            all_codes = re.findall(r'\b([a-zA-Z0-9]{6,8})\b', original_body)
            if all_codes:
                # 8 karakterli alfanumerik olanları tercih et (X formatı)
                eight_char = [code for code in all_codes if len(code) == 8 and re.match(r'^[a-zA-Z0-9]+$', code)]
                if eight_char:
                    self.logger.info("✅ Found 8-character alphanumeric code in fallback search")
                    return eight_char[0]
                
                # 6 haneli olanları dene
                six_digit = [code for code in all_codes if len(code) == 6]
                if six_digit:
                    self.logger.info("✅ Found 6-character code in fallback search")
                    return six_digit[0]
        
            return None
        
        except Exception as e:
            self.logger.error(f"❌ Error extracting verification code: {e}")
            return None
