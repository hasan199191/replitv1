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
        # Gmail App Password'u boşluksuz al
        app_password = os.environ.get('GMAIL_APP_PASSWORD', '')
        if app_password:
            # Boşlukları kaldır
            self.email_pass = app_password.replace(' ', '')
            self.logger = logging.getLogger('EmailHandler')
            self.logger.info(f"🔐 Using Gmail App Password (length: {len(self.email_pass)})")
        else:
            # Fallback normal şifre
            self.email_pass = "Nuray1965+"
            self.logger = logging.getLogger('EmailHandler')
            self.logger.warning("⚠️ Using regular password - App Password recommended!")
        
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        self.setup_logging()
        
    def setup_logging(self):
        """Loglama ayarlarını yapılandır"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def get_twitter_verification_code(self, timeout=90) -> Optional[str]:
        """Twitter'dan gelen doğrulama kodunu email'den al - BASİTLEŞTİRİLMİŞ"""
        try:
            self.logger.info("📧 Connecting to Gmail for verification code...")
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # Gmail'e bağlan
                    mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
                    mail.login(self.email_user, self.email_pass)
                    mail.select('inbox')
                    
                    # Son 50 email'i al (basit arama)
                    result, data = mail.search(None, 'ALL')
                    
                    if data[0]:
                        email_ids = data[0].split()
                        
                        # En son 50 email'i kontrol et
                        for email_id in reversed(email_ids[-50:]):
                            result, data = mail.fetch(email_id, '(RFC822)')
                            
                            if data[0]:
                                email_message = email.message_from_bytes(data[0][1])
                                
                                # Email konusunu kontrol et
                                subject = email_message.get('Subject', '')
                                sender = email_message.get('From', '')
                                
                                # Twitter/X doğrulama email'i mi?
                                if any(keyword in subject.lower() for keyword in ['verification', 'confirm', 'code', 'verify', 'security', 'login', 'twitter', 'x confirmation']) or any(domain in sender.lower() for domain in ['twitter.com', 'x.com']):
                                    
                                    self.logger.info(f"📧 Found potential verification email: {subject}")
                                    
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
                    
                    mail.close()
                    mail.logout()
                    
                    # 10 saniye bekle ve tekrar dene
                    self.logger.info("⏳ No verification code found, waiting 10 seconds...")
                    time.sleep(10)
                    
                except Exception as e:
                    self.logger.error(f"❌ Error checking email: {e}")
                    time.sleep(10)
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
                # X confirmation code formatları
                r'Your X confirmation code is\s*([a-zA-Z0-9]{6,8})',
                r'confirmation code is\s*([a-zA-Z0-9]{6,8})',
                r'single-use code[.\s]*([a-zA-Z0-9]{6,8})',
                
                # Geleneksel formatlar
                r'verification code[:\s]*([0-9]{6})',
                r'code[:\s]*([0-9]{6})',
                r'confirm[:\s]*([0-9]{6})',
                r'([0-9]{6})',
                r'([0-9]{4})',
                r'([0-9]{8})',
                
                # Alfanumerik kodlar
                r'([a-zA-Z0-9]{8})',
                r'([a-zA-Z0-9]{6})',
            ]
            
            email_lower = email_body.lower()
            
            # Önce X spesifik pattern'leri dene
            x_patterns = [
                r'your x confirmation code is\s*([a-zA-Z0-9]{6,8})',
                r'confirmation code is\s*([a-zA-Z0-9]{6,8})',
                r'single-use code[.\s]*([a-zA-Z0-9]{6,8})',
            ]
            
            for pattern in x_patterns:
                matches = re.findall(pattern, email_lower, re.IGNORECASE)
                if matches:
                    code = matches[0]
                    if len(code) in [4, 6, 8]:
                        self.logger.info(f"✅ Found X verification code with pattern: {pattern}")
                        return code
            
            # Sonra genel pattern'leri dene
            for pattern in patterns:
                matches = re.findall(pattern, email_lower, re.IGNORECASE)
                
                if matches:
                    # En uzun kodu al
                    code = max(matches, key=len)
                    
                    # Kod uzunluğu kontrolü
                    if len(code) in [4, 6, 8]:
                        self.logger.info(f"✅ Found verification code with pattern: {pattern}")
                        return code
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting verification code: {e}")
            return None
