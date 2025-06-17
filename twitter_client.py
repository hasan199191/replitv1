import tweepy
import json
import os
import logging
from typing import Optional, Dict, List
import aiofiles
import asyncio

class TwitterClient:
    def __init__(self):
        self.api = None
        self.client = None
        self.session_file = 'data/twitter_session.json'
        self.credentials_file = 'data/twitter_credentials.json'
        
    async def initialize(self):
        """Twitter client'ı başlat"""
        try:
            # Kimlik bilgilerini yükle
            credentials = await self.load_credentials()
            
            if not credentials:
                raise Exception("Twitter kimlik bilgileri bulunamadı")
            
            # Twitter API v2 client
            self.client = tweepy.Client(
                bearer_token=credentials.get('bearer_token'),
                consumer_key=credentials.get('api_key'),
                consumer_secret=credentials.get('api_secret'),
                access_token=credentials.get('access_token'),
                access_token_secret=credentials.get('access_token_secret'),
                wait_on_rate_limit=True
            )
            
            # Twitter API v1.1 (bazı özellikler için)
            auth = tweepy.OAuth1UserHandler(
                credentials.get('api_key'),
                credentials.get('api_secret'),
                credentials.get('access_token'),
                credentials.get('access_token_secret')
            )
            
            self.api = tweepy.API(auth, wait_on_rate_limit=True)
            
            # Bağlantıyı test et
            user = self.client.get_me()
            if user.data:
                logging.info(f"Twitter'a başarıyla bağlanıldı: @{user.data.username}")
                await self.save_session_data(user.data)
                return True
            else:
                raise Exception("Twitter bağlantısı test edilemedi")
                
        except Exception as e:
            logging.error(f"Twitter client başlatılırken hata: {e}")
            raise
    
    async def load_credentials(self):
        """Twitter kimlik bilgilerini yükle"""
        try:
            if os.path.exists(self.credentials_file):
                async with aiofiles.open(self.credentials_file, 'r') as f:
                    content = await f.read()
                    return json.loads(content)
            else:
                # Örnek kimlik bilgileri dosyası oluştur
                await self.create_sample_credentials_file()
                logging.warning("Lütfen twitter_credentials.json dosyasını gerçek bilgilerle doldurun")
                return None
        except Exception as e:
            logging.error(f"Kimlik bilgileri yüklenirken hata: {e}")
            return None
    
    async def create_sample_credentials_file(self):
        """Örnek kimlik bilgileri dosyası oluştur"""
        os.makedirs('data', exist_ok=True)
        sample_credentials = {
            "api_key": "YOUR_API_KEY",
            "api_secret": "YOUR_API_SECRET",
            "bearer_token": "YOUR_BEARER_TOKEN",
            "access_token": "YOUR_ACCESS_TOKEN",
            "access_token_secret": "YOUR_ACCESS_TOKEN_SECRET"
        }
        
        async with aiofiles.open(self.credentials_file, 'w') as f:
            await f.write(json.dumps(sample_credentials, indent=2))
    
    async def save_session_data(self, user_data):
        """Session verilerini kaydet"""
        try:
            os.makedirs('data', exist_ok=True)
            session_data = {
                "user_id": user_data.id,
                "username": user_data.username,
                "name": user_data.name,
                "last_login": str(asyncio.get_event_loop().time())
            }
            
            async with aiofiles.open(self.session_file, 'w') as f:
                await f.write(json.dumps(session_data, indent=2))
                
            logging.info("Session verileri kaydedildi")
            
        except Exception as e:
            logging.error(f"Session verileri kaydedilirken hata: {e}")
    
    async def post_tweet(self, content: str) -> bool:
        """Tweet gönder"""
        try:
            if len(content) > 280:
                content = content[:277] + "..."
            
            response = self.client.create_tweet(text=content)
            
            if response.data:
                logging.info(f"Tweet gönderildi: {response.data['id']}")
                return True
            else:
                logging.error("Tweet gönderilemedi")
                return False
                
        except Exception as e:
            logging.error(f"Tweet gönderilirken hata: {e}")
            return False
    
    async def reply_to_tweet(self, tweet_id: str, reply_content: str) -> bool:
        """Tweet'e yanıt ver"""
        try:
            if len(reply_content) > 280:
                reply_content = reply_content[:277] + "..."
            
            response = self.client.create_tweet(
                text=reply_content,
                in_reply_to_tweet_id=tweet_id
            )
            
            if response.data:
                logging.info(f"Yanıt gönderildi: {response.data['id']}")
                return True
            else:
                logging.error("Yanıt gönderilemedi")
                return False
                
        except Exception as e:
            logging.error(f"Yanıt gönderilirken hata: {e}")
            return False
    
    async def follow_user(self, username: str) -> bool:
        """Kullanıcıyı takip et"""
        try:
            # Kullanıcı bilgilerini al
            user = self.client.get_user(username=username)
            
            if user.data:
                # Takip et
                response = self.client.follow_user(user.data.id)
                
                if response.data:
                    logging.info(f"@{username} takip edildi")
                    return True
                else:
                    logging.warning(f"@{username} zaten takip ediliyor olabilir")
                    return True
            else:
                logging.error(f"@{username} kullanıcısı bulunamadı")
                return False
                
        except Exception as e:
            logging.error(f"@{username} takip edilirken hata: {e}")
            return False
    
    async def get_latest_tweet(self, username: str) -> Optional[Dict]:
        """Kullanıcının son tweet'ini al"""
        try:
            # Kullanıcı bilgilerini al
            user = self.client.get_user(username=username)
            
            if user.data:
                # Kullanıcının tweet'lerini al
                tweets = self.client.get_users_tweets(
                    user.data.id,
                    max_results=5,
                    exclude=['retweets', 'replies']
                )
                
                if tweets.data and len(tweets.data) > 0:
                    latest_tweet = tweets.data[0]
                    return {
                        'id': latest_tweet.id,
                        'text': latest_tweet.text,
                        'created_at': latest_tweet.created_at
                    }
                else:
                    logging.warning(f"@{username} için tweet bulunamadı")
                    return None
            else:
                logging.error(f"@{username} kullanıcısı bulunamadı")
                return None
                
        except Exception as e:
            logging.error(f"@{username} son tweet'i alınırken hata: {e}")
            return None
