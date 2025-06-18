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
        self.email_pass = "Nuray1965+"  # Direkt şifre
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
    
    def get_twitter_verification_code(self, timeout=90) -> Optional[str]:
        """Twitter'dan gelen doğrulama kodunu email'den al"""
        try:
            # Environment variable'dan al, yoksa direkt şifreyi kullan
            self.email_pass = os.environ.get('GMAIL_APP_PASSWORD') or os.environ.get('EMAIL_PASS') or "Nuray1965+"
        
            if not self.email_pass:
                self.logger.error("❌ No email password available!")
                return None
    
            self.logger.info("📧 Connecting to Gmail...")
        
            start_time = time.time()
        
            while time.time() - start_time < timeout:
                try:
                    # Gmail'e bağlan
                    mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
                    mail.login(self.email_user, self.email_pass)
                    mail.select('inbox')
                
                    # Son 10 dakikadaki Twitter emaillerini ara - DÜZELTME
                    import datetime
                    since_date = (datetime.datetime.now() - datetime.timedelta(minutes=10)).strftime('%d-%b-%Y')
                
                    # Basit search criteria - DÜZELTME
                    search_criteria = f'(FROM "verify@twitter.com" OR FROM "info@twitter.com" OR FROM "noreply@twitter.com") SINCE {since_date}'
                
                    result, data = mail.search(None, search_criteria)
                
                    if result == 'OK' and data[0]:
                        email_ids = data[0].split()
                    
                        # En son email'leri kontrol et
                        for email_id in reversed(email_ids[-5:]):  # Son 5 email
                            try:
                                result, data = mail.fetch(email_id, '(RFC822)')
                            
                                if data[0]:
                                    email_message = email.message_from_bytes(data[0][1])
                                
                                    # Email konusunu kontrol et
                                    subject = email_message.get('Subject', '')
                                    self.logger.info(f"📧 Checking email: {subject}")
                                
                                    # Twitter doğrulama email'i mi?
                                    if any(keyword in subject.lower() for keyword in ['verification', 'confirm', 'code', 'verify', 'security', 'login']):
                                    
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
                            except Exception as e:
                                self.logger.warning(f"⚠️ Error processing email: {e}")
                                continue
                
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
        """Email içeriğinden doğrulama kodunu çıkar"""
        try:
            # Farklı doğrulama kodu formatları
            patterns = [
                r'verification code[:\s]*([0-9]{6})',  # verification code: 123456
                r'code[:\s]*([0-9]{6})',               # code: 123456
                r'confirm[:\s]*([0-9]{6})',            # confirm: 123456
                r'([0-9]{6})',                         # sadece 6 haneli sayı
                r'verification code[:\s]*([0-9]{4})',  # 4 haneli kod
                r'code[:\s]*([0-9]{4})',               # 4 haneli kod
                r'([0-9]{4})',                         # sadece 4 haneli sayı
                r'([0-9]{8})',                         # 8 haneli kod
            ]
            
            email_lower = email_body.lower()
            
            for pattern in patterns:
                matches = re.findall(pattern, email_lower, re.IGNORECASE)
                
                if matches:
                    # En uzun kodu al (genellikle doğrulama kodu)
                    code = max(matches, key=len)
                    
                    # Kod uzunluğu kontrolü
                    if len(code) in [4, 6, 8]:
                        return code
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting verification code: {e}")
            return None
