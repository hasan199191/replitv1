import asyncio
import schedule
import time
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
import random
from twitter_browser import TwitterBrowser
from advanced_content_generator import AdvancedContentGenerator
from health_server import start_health_server

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

class TwitterBot:
    def __init__(self):
        self.twitter_browser = None
        self.content_generator = AdvancedContentGenerator()
        self.is_running = False
        self.health_server = None
        self.bot_initialized = False
        self.initialization_attempts = 0
        self.max_init_attempts = 3
        
    async def initialize(self):
        """Bot'u başlat ve Twitter'a giriş yap - GELİŞTİRİLMİŞ"""
        try:
            self.initialization_attempts += 1
            logging.info(f"🤖 Initializing Twitter Bot (Attempt {self.initialization_attempts}/{self.max_init_attempts})...")
            
            # Health server'ı başlat (Render için gerekli)
            if os.environ.get('IS_RENDER'):
                self.health_server = start_health_server()
                logging.info("🏥 Health server started for Render.com")
            
            # İçerik üreticisini başlat
            await self.content_generator.initialize()
            logging.info("🧠 Content generator initialized")
            
            # Twitter tarayıcısını başlat (Playwright)
            self.twitter_browser = TwitterBrowser()
            if not await self.twitter_browser.initialize():
                raise Exception("Twitter browser could not be initialized")
            
            # Twitter'a giriş yap - SADECE GEREKTİĞINDE
            login_success = await self.twitter_browser.quick_login_check()
            if not login_success:
                logging.info("🔐 Login required, attempting to login...")
                login_success = await self.twitter_browser.login()
            
            if not login_success:
                if self.initialization_attempts < self.max_init_attempts:
                    logging.warning(f"⚠️ Login failed, waiting 5 minutes before retry...")
                    await asyncio.sleep(300)  # 5 dakika bekle
                    return await self.initialize()  # Recursive retry
                else:
                    raise Exception("Could not login to Twitter after multiple attempts")
            
            self.bot_initialized = True
            logging.info("🎉 Bot successfully initialized!")
            logging.info("📱 Session management active - minimal login attempts!")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Error initializing bot: {e}")
            if self.initialization_attempts < self.max_init_attempts:
                logging.info(f"🔄 Retrying initialization in 10 minutes...")
                await asyncio.sleep(600)  # 10 dakika bekle
                return await self.initialize()
            return False
    
    async def hourly_workflow(self):
        """Saatlik workflow - DAHA GÜVENLE"""
        try:
            logging.info("⏰ Starting hourly workflow...")
            
            # Session durumunu kontrol et
            if not await self.twitter_browser.quick_login_check():
                logging.warning("⚠️ Session lost, attempting to restore...")
                if not await self.twitter_browser.login():
                    logging.error("❌ Could not restore session, skipping this cycle")
                    return
            
            # 1. İki Web3 projesi seç ve paylaş
            await self.post_project_content()
            
            # Projeler arası uzun bekleme
            await asyncio.sleep(random.uniform(120, 180))  # 2-3 dakika
            
            # 2. Takip edilen hesapların tweetlerine yanıt ver
            await self.reply_to_monitored_tweets()
            
            logging.info("✅ Hourly workflow completed!")
            
        except Exception as e:
            logging.error(f"❌ Error in hourly workflow: {e}")
    
    async def post_project_content(self):
        """2 Web3 projesi seç ve içerik paylaş - DAHA GÜVENLE"""
        try:
            logging.info("🚀 Selecting and posting Web3 project content...")
            
            # 2 proje seç
            selected_projects = self.content_generator.select_random_projects(2)
            logging.info(f"📋 Selected projects: {[p['name'] for p in selected_projects]}")
            
            for i, project in enumerate(selected_projects):
                try:
                    # İçerik üret
                    content = await self.content_generator.generate_project_content(project)
                    
                    if content:
                        # Tweet gönder
                        success = await self.twitter_browser.post_tweet(content)
                        if success:
                            logging.info(f"✅ Posted content for {project['name']}")
                            logging.info(f"📝 Content: {content[:100]}...")
                        else:
                            logging.error(f"❌ Failed to post content for {project['name']}")
                    else:
                        logging.error(f"❌ No content generated for {project['name']}")
                    
                    # Projeler arası uzun bekleme (rate limit koruması)
                    if i < len(selected_projects) - 1:
                        wait_time = random.uniform(60, 90)  # 1-1.5 dakika
                        logging.info(f"⏳ Waiting {wait_time:.1f} seconds before next project...")
                        await asyncio.sleep(wait_time)
                        
                except Exception as e:
                    logging.error(f"❌ Error processing project {project['name']}: {e}")
                    continue
                
        except Exception as e:
            logging.error(f"❌ Error in project content posting: {e}")
    
    async def reply_to_monitored_tweets(self):
        """Takip edilen hesapların son tweetlerine yanıt ver - DAHA GÜVENLE"""
        try:
            logging.info("💬 Checking monitored accounts for replies...")
            
            # Sadece 2 hesap seç (rate limit için daha da azalttık)
            selected_accounts = self.content_generator.get_random_accounts(2)
            logging.info(f"👥 Selected accounts: {selected_accounts}")
            
            for i, username in enumerate(selected_accounts):
                try:
                    # Kullanıcıyı takip et
                    await self.twitter_browser.follow_user(username)
                    
                    # Takip sonrası bekleme
                    await asyncio.sleep(random.uniform(10, 20))
                    
                    # Son tweet'i al
                    tweet_data = await self.twitter_browser.get_latest_tweet(username)
                    
                    if tweet_data and tweet_data.get('url'):
                        # Tweet zamanını kontrol et (son 3 saat içinde mi?)
                        if tweet_data.get('time'):
                            tweet_time = datetime.fromisoformat(tweet_data['time'].replace('Z', '+00:00'))
                            now = datetime.now().astimezone()
                            
                            if now - tweet_time < timedelta(hours=3):
                                # Yanıt üret
                                reply_content = await self.content_generator.generate_reply(tweet_data)
                                
                                if reply_content:
                                    # Yanıt gönder
                                    success = await self.twitter_browser.reply_to_tweet(
                                        tweet_data['url'], 
                                        reply_content
                                    )
                                    
                                    if success:
                                        logging.info(f"✅ Replied to @{username}")
                                        logging.info(f"💬 Reply: {reply_content[:100]}...")
                                    else:
                                        logging.error(f"❌ Failed to reply to @{username}")
                                else:
                                    logging.error(f"❌ No reply generated for @{username}")
                            else:
                                logging.info(f"⏰ @{username}'s tweet is older than 3 hours, skipping")
                        else:
                            logging.warning(f"⚠️ Could not determine tweet time for @{username}")
                    else:
                        logging.warning(f"⚠️ No recent tweets found for @{username}")
                    
                    # Hesaplar arası çok uzun bekleme (rate limit koruması)
                    if i < len(selected_accounts) - 1:
                        wait_time = random.uniform(180, 240)  # 3-4 dakika
                        logging.info(f"⏳ Waiting {wait_time/60:.1f} minutes before next account...")
                        await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    logging.error(f"❌ Error processing @{username}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"❌ Error in reply workflow: {e}")
    
    def schedule_tasks(self):
        """Görevleri zamanla - Her 2 saatte bir çalışacak"""
        # Her 2 saatte bir workflow çalıştır (rate limit için)
        schedule.every(2).hours.do(
            lambda: asyncio.create_task(self.hourly_workflow())
        )
        
        logging.info("📅 Scheduled workflow every 2 hours (reduced frequency)")
    
    def signal_handler(self, signum, frame):
        """Shutdown signal handler"""
        logging.info(f"🛑 Received signal {signum}, shutting down gracefully...")
        self.is_running = False
        if self.twitter_browser:
            asyncio.create_task(self.twitter_browser.close())
        sys.exit(0)
    
    async def run(self):
        """Bot'u çalıştır"""
        # Signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Bot'u başlat
        if not await self.initialize():
            logging.error("❌ Bot could not be initialized")
            return
        
        self.is_running = True
        self.schedule_tasks()
        
        logging.info("🤖 Twitter Bot is now running with enhanced stealth!")
        logging.info("⏰ Will execute workflow every 2 hours")
        logging.info("🛡️ Anti-detection measures active")
        logging.info("📱 Persistent session with minimal login attempts")
        
        # İlk workflow'u 10 dakika sonra çalıştır (hemen değil)
        logging.info("🚀 First workflow will start in 10 minutes...")
        await asyncio.sleep(600)  # 10 dakika bekle
        await self.hourly_workflow()
        
        # Ana döngü - Sürekli çalış
        while self.is_running:
            try:
                schedule.run_pending()
                await asyncio.sleep(300)  # Her 5 dakika kontrol et
                
                # Her 12 saatte bir session durumunu kontrol et
                current_time = datetime.now()
                if current_time.minute == 0 and current_time.hour % 12 == 0:
                    logging.info("🔍 Periodic session health check...")
                    if not await self.twitter_browser.quick_login_check():
                        logging.warning("⚠️ Session lost during health check")
                        # Login yapmaya çalışma, sadece log tut
                        # Bir sonraki workflow'da otomatik düzelecek
                    
            except Exception as e:
                logging.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(300)

async def main():
    bot = TwitterBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        logging.info("🛑 Bot stopped by user")
    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")
    finally:
        # Temiz kapatma
        if bot.twitter_browser:
            await bot.twitter_browser.close()
        logging.info("👋 Bot shutdown complete")

if __name__ == "__main__":
    # Logs klasörünü oluştur
    os.makedirs('logs', exist_ok=True)
    
    # Bot'u çalıştır
    asyncio.run(main())
