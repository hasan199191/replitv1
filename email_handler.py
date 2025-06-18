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
    
    def get_twitter_verification_code(self, timeout=120) -> Optional[str]:
        """Twitter'dan gelen doğrulama kodunu email'den al - GELİŞTİRİLMİŞ"""
        try:
            # Environment variable'dan al, yoksa direkt şifreyi kullan
            self.email_pass = os.environ.get('EMAIL_PASS') or "Nuray1965+"
        
            if not self.email_pass:
                self.logger.error("❌ No email password available!")
                return None
    
            self.logger.info("📧 Connecting to Gmail for verification code...")
        
            start_time = time.time()
        
            while time.time() - start_time < timeout:
                try:
                    # Gmail'e bağlan
                    mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
                    mail.login(self.email_user, self.email_pass)
                    mail.select('inbox')
                
                    # Son 15 dakikadaki Twitter emaillerini ara (daha geniş arama)
                    search_criteria = '(FROM "verify@twitter.com" OR FROM "info@twitter.com" OR FROM "noreply@twitter.com" OR FROM "account@twitter.com" OR FROM "security@twitter.com" OR SUBJECT "Twitter" OR SUBJECT "verification" OR SUBJECT "code") SINCE "' + time.strftime('%d-%b-%Y', time.gmtime(time.time() - 900)) + '"'
                
                    result, data = mail.search(None, search_criteria)
                
                    if data[0]:
                        email_ids = data[0].split()
                    
                        # En son email'leri kontrol et (son 20 email)
                        for email_id in reversed(email_ids[-20:]):
                            result, data = mail.fetch(email_id, '(RFC822)')
                        
                            if data[0]:
                                email_message = email.message_from_bytes(data[0][1])
                            
                                # Email konusunu kontrol et
                                subject = email_message.get('Subject', '')
                                sender = email_message.get('From', '')
                                self.logger.info(f"📧 Checking email from {sender}: {subject}")
                            
                                # Twitter doğrulama email'i mi?
                                if any(keyword in subject.lower() for keyword in ['verification', 'confirm', 'code', 'verify', 'security', 'login', 'twitter']) or any(domain in sender.lower() for domain in ['twitter.com', 'x.com']):
                                
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
        """Email içeriğinden doğrulama kodunu çıkar - GELİŞTİRİLMİŞ"""
        try:
            # Farklı doğrulama kodu formatları - daha kapsamlı
            patterns = [
                r'verification code[:\s]*([0-9]{6})',  # verification code: 123456
                r'confirmation code[:\s]*([0-9]{6})',  # confirmation code: 123456
                r'security code[:\s]*([0-9]{6})',      # security code: 123456
                r'login code[:\s]*([0-9]{6})',         # login code: 123456
                r'code[:\s]*([0-9]{6})',               # code: 123456
                r'confirm[:\s]*([0-9]{6})',            # confirm: 123456
                r'verify[:\s]*([0-9]{6})',             # verify: 123456
                r'([0-9]{6})',                         # sadece 6 haneli sayı
                r'verification code[:\s]*([0-9]{4})',  # 4 haneli kod
                r'code[:\s]*([0-9]{4})',               # 4 haneli kod
                r'([0-9]{4})',                         # sadece 4 haneli sayı
                r'([0-9]{8})',                         # 8 haneli kod
                # HTML formatları
                r'<.*?>([0-9]{6})<.*?>',               # HTML tag içinde 6 haneli
                r'<.*?>([0-9]{4})<.*?>',               # HTML tag içinde 4 haneli
                # Özel Twitter formatları
                r'Your Twitter confirmation code is[:\s]*([0-9]{6})',
                r'Your verification code is[:\s]*([0-9]{6})',
                r'Enter this code[:\s]*([0-9]{6})',
            ]
        
            email_lower = email_body.lower()
        
            # Önce spesifik Twitter pattern'lerini dene
            twitter_patterns = [
                r'your twitter confirmation code is[:\s]*([0-9]{6})',
                r'your verification code is[:\s]*([0-9]{6})',
                r'enter this code[:\s]*([0-9]{6})',
                r'verification code[:\s]*([0-9]{6})',
            ]
        
            for pattern in twitter_patterns:
                matches = re.findall(pattern, email_lower, re.IGNORECASE)
                if matches:
                    code = matches[0]
                    if len(code) in [4, 6, 8]:
                        self.logger.info(f"✅ Found code with Twitter pattern: {pattern}")
                        return code
        
            # Sonra genel pattern'leri dene
            for pattern in patterns:
                matches = re.findall(pattern, email_lower, re.IGNORECASE)
            
                if matches:
                    # En uzun kodu al (genellikle doğrulama kodu)
                    code = max(matches, key=len)
                
                    # Kod uzunluğu kontrolü
                    if len(code) in [4, 6, 8]:
                        self.logger.info(f"✅ Found code with pattern: {pattern}")
                        return code
        
            # Son çare: email body'de tüm sayıları bul ve en uygun olanı seç
            all_numbers = re.findall(r'\b([0-9]{4,8})\b', email_body)
            if all_numbers:
                # 6 haneli olanları tercih et
                six_digit = [num for num in all_numbers if len(num) == 6]
                if six_digit:
                    self.logger.info("✅ Found 6-digit code in fallback search")
                    return six_digit[0]
            
                # 4 haneli olanları dene
                four_digit = [num for num in all_numbers if len(num) == 4]
                if four_digit:
                    self.logger.info("✅ Found 4-digit code in fallback search")
                    return four_digit[0]
        
            return None
        
        except Exception as e:
            self.logger.error(f"❌ Error extracting verification code: {e}")
            return None
