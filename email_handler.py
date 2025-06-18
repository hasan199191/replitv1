import imaplib
import email
import re
import time
import logging
import os
from typing import Optional
from datetime import datetime, timedelta

class EmailHandler:
    def __init__(self):
        # Multiple environment variable options
        self.email_user = (
            os.getenv('EMAIL_ADDRESS') or 
            os.getenv('EMAIL_USER') or 
            "hasanacikgoz91@gmail.com"  # Fallback
        )
        
        self.email_pass = (
            os.getenv('EMAIL_PASSWORD') or 
            os.getenv('GMAIL_APP_PASSWORD') or 
            os.getenv('EMAIL_PASS')
        )
        
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        self.logger = logging.getLogger('EmailHandler')
        self.setup_logging()
        
        # Debug logging
        self.logger.info(f"📧 Email Handler initialized")
        self.logger.info(f"   Email: {self.email_user}")
        self.logger.info(f"   Password: {'✅ Set' if self.email_pass else '❌ Not set'}")
        
    def setup_logging(self):
        """Loglama ayarlarını yapılandır"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    async def get_twitter_verification_code(self, timeout=120) -> Optional[str]:
        """Twitter'dan gelen doğrulama kodunu email'den al - ASYNC VERSION"""
        try:
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
                    
                    # Son 10 dakikadaki Twitter emaillerini ara
                    since_date = (datetime.now() - timedelta(minutes=10)).strftime('%d-%b-%Y')
                    
                    # Multiple search patterns for Twitter emails
                    search_patterns = [
                        f'(FROM "info@x.com" SUBJECT "confirmation code") SINCE {since_date}',
                        f'(FROM "verify@twitter.com") SINCE {since_date}',
                        f'(FROM "info@twitter.com") SINCE {since_date}',
                        f'(FROM "noreply@twitter.com") SINCE {since_date}',
                        f'(SUBJECT "verification code") SINCE {since_date}',
                        f'(SUBJECT "confirmation code") SINCE {since_date}'
                    ]
                    
                    for pattern in search_patterns:
                        try:
                            result, data = mail.search(None, pattern)
                            
                            if data[0]:
                                email_ids = data[0].split()
                                self.logger.info(f"📧 Found {len(email_ids)} emails with pattern: {pattern}")
                                
                                # Check recent emails first
                                for email_id in reversed(email_ids[-5:]):  # Last 5 emails
                                    try:
                                        result, data = mail.fetch(email_id, '(RFC822)')
                                        
                                        if data[0]:
                                            email_message = email.message_from_bytes(data[0][1])
                                            
                                            # Get email details
                                            subject = email_message.get('Subject', '')
                                            sender = email_message.get('From', '')
                                            date = email_message.get('Date', '')
                                            
                                            self.logger.info(f"📧 Checking email:")
                                            self.logger.info(f"   Subject: {subject}")
                                            self.logger.info(f"   From: {sender}")
                                            self.logger.info(f"   Date: {date}")
                                            
                                            # Check if it's a Twitter verification email
                                            if self.is_twitter_verification_email(subject, sender):
                                                # Try to extract code from subject first
                                                code = self.extract_code_from_subject(subject)
                                                
                                                if not code:
                                                    # Try to extract from body
                                                    body = self.get_email_body(email_message)
                                                    if body:
                                                        code = self.extract_verification_code(body)
                                                
                                                if code:
                                                    self.logger.info(f"✅ Found Twitter verification code: {code}")
                                                    mail.close()
                                                    mail.logout()
                                                    return code
                                    except Exception as e:
                                        self.logger.warning(f"⚠️ Error processing email: {e}")
                                        continue
                        except Exception as e:
                            self.logger.warning(f"⚠️ Search pattern failed: {pattern} - {e}")
                            continue
                    
                    mail.close()
                    mail.logout()
                    
                    # Wait before next check
                    self.logger.info("⏳ No verification code found, waiting 10 seconds...")
                    import asyncio
                    await asyncio.sleep(10)
                    
                except Exception as e:
                    self.logger.error(f"❌ Error checking email: {e}")
                    import asyncio
                    await asyncio.sleep(10)
                    continue
            
            self.logger.warning("⚠️ Timeout waiting for verification code")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error in email handler: {e}")
            return None
    
    def is_twitter_verification_email(self, subject: str, sender: str) -> bool:
        """Check if email is from Twitter/X for verification"""
        subject_lower = subject.lower()
        sender_lower = sender.lower()
        
        # Twitter/X domains
        twitter_domains = ['x.com', 'twitter.com', 'info@x.com', 'verify@twitter.com', 'info@twitter.com']
        
        # Verification keywords
        verification_keywords = ['verification', 'confirm', 'code', 'verify', 'security', 'login']
        
        # Check sender
        is_from_twitter = any(domain in sender_lower for domain in twitter_domains)
        
        # Check subject
        has_verification_keyword = any(keyword in subject_lower for keyword in verification_keywords)
        
        return is_from_twitter and has_verification_keyword
    
    def extract_code_from_subject(self, subject: str) -> Optional[str]:
        """Extract verification code directly from email subject"""
        try:
            # Pattern for "Your X confirmation code is 123456"
            patterns = [
                r'confirmation code is (\d{4,8})',
                r'verification code is (\d{4,8})',
                r'code is (\d{4,8})',
                r'Your X confirmation code is (\d{4,8})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, subject, re.IGNORECASE)
                if match:
                    code = match.group(1)
                    if len(code) in [4, 6, 8]:  # Valid code lengths
                        return code
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting code from subject: {e}")
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
                r'confirmation code[:\s]*([0-9]{6})',  # confirmation code: 123456
                r'code[:\s]*([0-9]{6})',               # code: 123456
                r'confirm[:\s]*([0-9]{6})',            # confirm: 123456
                r'([0-9]{6})',                         # sadece 6 haneli sayı
                r'verification code[:\s]*([0-9]{4})',  # 4 haneli kod
                r'confirmation code[:\s]*([0-9]{4})',  # 4 haneli kod
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

    # Backward compatibility - sync version
    def get_verification_code(self, timeout=120):
        """Sync version for backward compatibility"""
        import asyncio
        return asyncio.run(self.get_twitter_verification_code(timeout))
