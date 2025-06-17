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
        self.bot_start_time = datetime.now()
        
    async def initialize(self):
        """Bot'u başlat ve Twitter'a giriş yap"""
        try:
            self.initialization_attempts += 1
            logging.info(f"🤖 Initializing Twitter Bot (Attempt {self.initialization_attempts}/{self.max_init_attempts})...")
            
            # Bot başlangıç zamanını kaydet
            self.bot_start_time = datetime.now()
            logging.info(f"🕐 Bot start time: {self.bot_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
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
    
    async def complete_workflow(self):
        """KOMPLE WORKFLOW - 2 Görev: Proje Paylaşımı + Reply Kontrolü"""
        try:
            logging.info("🔄 Starting COMPLETE workflow...")
            
            # Session durumunu kontrol et
            if not await self.twitter_browser.quick_login_check():
                logging.warning("⚠️ Session lost, attempting to restore...")
                if not await self.twitter_browser.login():
                    logging.error("❌ Could not restore session, skipping this cycle")
                    return
            
            # GÖREV 1: 2 Web3 projesi seç ve paylaş
            logging.info("📋 TASK 1: Posting Web3 project content...")
            await self.post_project_content()
            
            # Görevler arası bekleme
            await asyncio.sleep(random.uniform(60, 90))  # 1-1.5 dakika
            
            # GÖREV 2: Takip edilen hesapları kontrol et ve yanıt ver
            logging.info("💬 TASK 2: Checking monitored accounts for replies...")
            await self.reply_to_all_recent_tweets()
            
            logging.info("✅ COMPLETE workflow finished!")
            
        except Exception as e:
            logging.error(f"❌ Error in complete workflow: {e}")
    
    async def post_project_content(self):
        """GÖREV 1: 2 Web3 projesi seç ve içerik paylaş"""
        try:
            logging.info("🚀 Selecting and posting Web3 project content...")
            
            # Projects listesinden 2 proje seç
            selected_projects = self.content_generator.select_random_projects(2)
            logging.info(f"📋 Selected projects: {[p['name'] for p in selected_projects]}")
            
            for i, project in enumerate(selected_projects):
                try:
                    logging.info(f"📝 Processing project {i+1}/2: {project['name']}")
                    
                    # Gemini ile içerik üret
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
                        wait_time = random.uniform(30, 60)  # 30-60 saniye
                        logging.info(f"⏳ Waiting {wait_time:.1f} seconds before next project...")
                        await asyncio.sleep(wait_time)
                        
                except Exception as e:
                    logging.error(f"❌ Error processing project {project['name']}: {e}")
                    continue
            
            logging.info("✅ Project content posting completed!")
                
        except Exception as e:
            logging.error(f"❌ Error in project content posting: {e}")
    
    async def reply_to_all_recent_tweets(self):
        """GÖREV 2: Monitored accounts listesindeki hesapları kontrol et ve yanıt ver"""
        try:
            logging.info("💬 Checking monitored accounts for recent tweets...")
            
            # Monitored accounts listesinden TÜM hesapları al
            all_accounts = self.content_generator.monitored_accounts
            logging.info(f"👥 Total monitored accounts to check: {len(all_accounts)}")
            
            # Son 1 saat içinde tweet atan hesapları bul
            recent_tweeters = []
            current_time = datetime.now()
            one_hour_ago = current_time - timedelta(hours=1)
            
            logging.info(f"🕐 Looking for tweets after: {one_hour_ago.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Her monitored account'u sırasıyla kontrol et
            for i, username in enumerate(all_accounts):
                try:
                    logging.info(f"🔍 Checking @{username} ({i+1}/{len(all_accounts)})")
                    
                    # Kullanıcıyı takip et (eğer değilse)
                    await self.twitter_browser.follow_user(username)
                    await asyncio.sleep(random.uniform(2, 5))  # Kısa bekleme
                    
                    # Son tweet'i al
                    tweet_data = await self.twitter_browser.get_latest_tweet(username)
                    
                    if tweet_data and tweet_data.get('url') and tweet_data.get('time'):
                        try:
                            # Tweet zamanını parse et
                            tweet_time = datetime.fromisoformat(tweet_data['time'].replace('Z', '+00:00'))
                            tweet_time_local = tweet_time.astimezone()
                            
                            # Son 1 saat içinde mi?
                            if tweet_time_local > one_hour_ago:
                                recent_tweeters.append({
                                    'username': username,
                                    'tweet_data': tweet_data,
                                    'tweet_time': tweet_time_local
                                })
                                logging.info(f"✅ @{username} tweeted recently at {tweet_time_local.strftime('%H:%M:%S')}")
                            else:
                                logging.info(f"⏰ @{username}'s last tweet is older than 1 hour")
                        except Exception as time_error:
                            logging.warning(f"⚠️ Could not parse tweet time for @{username}: {time_error}")
                    else:
                        logging.info(f"ℹ️ No recent tweets found for @{username}")
                    
                    # Her hesap kontrolü arasında kısa bekleme (rate limit için)
                    if i < len(all_accounts) - 1:
                        await asyncio.sleep(random.uniform(3, 8))  # 3-8 saniye
                        
                except Exception as e:
                    logging.error(f"❌ Error checking @{username}: {e}")
                    continue
            
            # Son 1 saat içinde tweet atan hesapları logla
            logging.info(f"🎯 Found {len(recent_tweeters)} accounts with recent tweets")
            
            if recent_tweeters:
                for tweeter in recent_tweeters:
                    logging.info(f"📝 @{tweeter['username']} - {tweeter['tweet_time'].strftime('%H:%M:%S')}")
            
            # Recent tweeters'a yanıt ver
            await self.reply_to_recent_tweeters(recent_tweeters)
            
            logging.info("✅ Reply checking completed!")
                    
        except Exception as e:
            logging.error(f"❌ Error in checking monitored accounts: {e}")
    
    async def reply_to_recent_tweeters(self, recent_tweeters):
        """Son 1 saat içinde tweet atan hesaplara Gemini ile yanıt üret ve gönder"""
        try:
            if not recent_tweeters:
                logging.info("ℹ️ No recent tweeters found to reply to")
                return
            
            logging.info(f"💬 Replying to {len(recent_tweeters)} recent tweets...")
            
            for i, tweeter in enumerate(recent_tweeters):
                try:
                    username = tweeter['username']
                    tweet_data = tweeter['tweet_data']
                    
                    logging.info(f"💬 Generating reply for @{username} ({i+1}/{len(recent_tweeters)})")
                    
                    # Gemini ile yanıt üret
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
                    
                    # Yanıtlar arası bekleme (rate limit koruması)
                    if i < len(recent_tweeters) - 1:
                        wait_time = random.uniform(30, 60)  # 30-60 saniye
                        logging.info(f"⏳ Waiting {wait_time:.1f} seconds before next reply...")
                        await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    logging.error(f"❌ Error replying to @{tweeter['username']}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"❌ Error in reply workflow: {e}")
    
    def schedule_tasks(self):
        """Görevleri zamanla - Her 2 saatte bir KOMPLE workflow"""
        # Her 2 saatte bir komple workflow çalıştır (2 görev birden)
        schedule.every(2).hours.do(
            lambda: asyncio.create_task(self.complete_workflow())
        )
        
        logging.info("📅 Scheduled COMPLETE workflow every 2 hours")
        logging.info("📋 Each cycle includes: Project posting + Reply checking")
    
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
        
        logging.info("🤖 Twitter Bot is now running with COMPLETE workflow!")
        logging.info("⏰ Will execute BOTH tasks every 2 hours")
        logging.info("📋 Task 1: Post 2 Web3 projects")
        logging.info("💬 Task 2: Reply to monitored accounts")
        logging.info("🛡️ Anti-detection measures active")
        logging.info("📱 Persistent session with minimal login attempts")
        logging.info(f"🚀 Projects available: {len(self.content_generator.projects)}")
        logging.info(f"👥 Monitored accounts: {len(self.content_generator.monitored_accounts)}")
        
        # İLK BAŞLANGIÇTA KOMPLE WORKFLOW ÇALIŞTIR
        logging.info("🚀 Starting initial COMPLETE workflow in 2 minutes...")
        await asyncio.sleep(120)  # 2 dakika bekle
        await self.complete_workflow()  # İlk komple workflow
        
        # Sonraki workflow'u 2 saat sonra çalıştır
        logging.info("🚀 Next COMPLETE workflow will start in 2 hours...")
        
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
