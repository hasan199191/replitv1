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
        
    async def initialize(self):
        """Bot'u başlat ve Twitter'a giriş yap"""
        try:
            logging.info("🤖 Initializing Twitter Bot with Playwright + Chromium...")
            
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
            
            # Twitter'a giriş yap - BU SADECE BİR KEZ YAPILACAK
            if not await self.twitter_browser.login():
                raise Exception("Could not login to Twitter")
            
            self.bot_initialized = True
            logging.info("🎉 Bot successfully initialized with Playwright!")
            logging.info("📱 Persistent session active - no repeated logins needed!")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Error initializing bot: {e}")
            return False
    
    async def hourly_workflow(self):
        """Saatlik workflow - 2 proje paylaş + tweet'lere yanıt ver"""
        try:
            logging.info("⏰ Starting hourly workflow...")
            
            # 1. İki Web3 projesi seç ve paylaş
            await self.post_project_content()
            
            # Projeler arası bekleme
            await asyncio.sleep(60)
            
            # 2. Takip edilen hesapların tweetlerine yanıt ver
            await self.reply_to_monitored_tweets()
            
            logging.info("✅ Hourly workflow completed!")
            
        except Exception as e:
            logging.error(f"❌ Error in hourly workflow: {e}")
    
    async def post_project_content(self):
        """2 Web3 projesi seç ve içerik paylaş"""
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
                    
                    # Projeler arası bekleme (rate limit koruması)
                    if i < len(selected_projects) - 1:
                        logging.info("⏳ Waiting 45 seconds before next project...")
                        await asyncio.sleep(45)
                        
                except Exception as e:
                    logging.error(f"❌ Error processing project {project['name']}: {e}")
                    continue
                
        except Exception as e:
            logging.error(f"❌ Error in project content posting: {e}")
    
    async def reply_to_monitored_tweets(self):
        """Takip edilen hesapların son tweetlerine yanıt ver"""
        try:
            logging.info("💬 Checking monitored accounts for replies...")
            
            # 3 hesap seç (rate limit için azalttık)
            selected_accounts = self.content_generator.get_random_accounts(3)
            logging.info(f"👥 Selected accounts: {selected_accounts}")
            
            for i, username in enumerate(selected_accounts):
                try:
                    # Kullanıcıyı takip et
                    await self.twitter_browser.follow_user(username)
                    
                    # Son tweet'i al
                    tweet_data = await self.twitter_browser.get_latest_tweet(username)
                    
                    if tweet_data and tweet_data.get('url'):
                        # Tweet zamanını kontrol et (son 2 saat içinde mi?)
                        if tweet_data.get('time'):
                            tweet_time = datetime.fromisoformat(tweet_data['time'].replace('Z', '+00:00'))
                            now = datetime.now().astimezone()
                            
                            if now - tweet_time < timedelta(hours=2):
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
                                logging.info(f"⏰ @{username}'s tweet is older than 2 hours, skipping")
                        else:
                            logging.warning(f"⚠️ Could not determine tweet time for @{username}")
                    else:
                        logging.warning(f"⚠️ No recent tweets found for @{username}")
                    
                    # Hesaplar arası bekleme (rate limit koruması)
                    if i < len(selected_accounts) - 1:
                        logging.info("⏳ Waiting 90 seconds before next account...")
                        await asyncio.sleep(90)
                    
                except Exception as e:
                    logging.error(f"❌ Error processing @{username}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"❌ Error in reply workflow: {e}")
    
    def schedule_tasks(self):
        """Görevleri zamanla - Her saat başı çalışacak"""
        # Her saat başında workflow çalıştır
        schedule.every().hour.at(":00").do(
            lambda: asyncio.create_task(self.hourly_workflow())
        )
        
        logging.info("📅 Scheduled hourly workflow (every hour at :00)")
    
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
        
        logging.info("🤖 Twitter Bot is now running with Playwright + Chromium!")
        logging.info("⏰ Will execute workflow every hour at :00")
        logging.info("📱 Persistent session active - much more reliable!")
        
        # İlk workflow'u hemen çalıştır
        logging.info("🚀 Running initial workflow...")
        await self.hourly_workflow()
        
        # Ana döngü - Sürekli çalış
        while self.is_running:
            try:
                schedule.run_pending()
                await asyncio.sleep(60)  # Her dakika kontrol et
                
                # Her 6 saatte bir session durumunu kontrol et
                current_time = datetime.now()
                if current_time.minute == 0 and current_time.hour % 6 == 0:
                    logging.info("🔍 Checking session health...")
                    if not await self.twitter_browser.check_login_status():
                        logging.warning("⚠️ Session lost, attempting to restore...")
                        if not await self.twitter_browser.login():
                            logging.error("❌ Could not restore session")
                        else:
                            logging.info("✅ Session restored")
                    
            except Exception as e:
                logging.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(60)

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
