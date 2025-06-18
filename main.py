import asyncio
import logging
import os
import sys
import time
import json
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from twitter_browser import TwitterBrowser
from advanced_content_generator import AdvancedContentGenerator
from email_handler import EmailHandler
from health_server import start_health_server

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

async def main():
    logging.info("🚀 Bot başlatılıyor...")
    print("🚀 Bot başlatılıyor...")

    # Health server'ı başlat (Render için gerekli)
    try:
        health_server = start_health_server()
        logging.info("✅ Health server başlatıldı")
    except Exception as e:
        logging.error(f"❌ Health server başlatılamadı: {e}")

    # Environment variables debug
    logging.info("🔍 Environment variables check:")
    env_vars = ['TWITTER_USERNAME', 'TWITTER_PASSWORD', 'EMAIL_ADDRESS', 'EMAIL_USER', 'EMAIL_PASSWORD', 'GMAIL_APP_PASSWORD', 'EMAIL_PASS', 'GEMINI_API_KEY']
    for var in env_vars:
        value = os.getenv(var)
        logging.info(f"   {var}: {'✅ Set' if value else '❌ Not set'}")

    # Gerekli environment değişkenlerini kontrol et
    TWITTER_USERNAME = os.getenv('TWITTER_USERNAME')
    TWITTER_PASSWORD = os.getenv('TWITTER_PASSWORD')
    if not TWITTER_USERNAME or not TWITTER_PASSWORD:
        logging.error("❌ Twitter kullanıcı adı veya şifre environment variables'da eksik!")
        print("❌ Twitter kullanıcı adı veya şifre environment variables'da eksik!")
        return

    # Email bilgilerini kontrol et
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS') or os.getenv('EMAIL_USER')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD') or os.getenv('GMAIL_APP_PASSWORD') or os.getenv('EMAIL_PASS')
    
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        logging.error("❌ Gmail bilgileri environment variables'da eksik!")
        print("❌ Gmail bilgileri environment variables'da eksik!")
        return
        
    if not os.getenv('GEMINI_API_KEY'):
        logging.error("❌ Gemini API anahtarı environment variables'da eksik!")
        print("❌ Gemini API anahtarı environment variables'da eksik!")
        return

    # Initialize components with retry logic
    max_init_retries = 3
    twitter = None
    content_generator = None
    
    for attempt in range(max_init_retries):
        try:
            logging.info(f"🔄 Initialization attempt {attempt + 1}/{max_init_retries}")
            
            # Initialize components
            email_handler = EmailHandler()
            content_generator = AdvancedContentGenerator()
            
            if not await content_generator.initialize():
                raise Exception("Gemini initialization failed")
            
            # Set environment variables for TwitterBrowser
            os.environ['TWITTER_USERNAME'] = TWITTER_USERNAME
            os.environ['TWITTER_PASSWORD'] = TWITTER_PASSWORD
            os.environ['EMAIL_USER'] = EMAIL_ADDRESS
            os.environ['EMAIL_PASS'] = EMAIL_PASSWORD
            
            twitter = TwitterBrowser()
            
            if not await twitter.initialize():
                raise Exception("Browser initialization failed")
            
            if not await twitter.login():
                raise Exception("Twitter login failed")
            
            # Login durumunu set et
            twitter.is_logged_in = True
            
            logging.info("✅ All components initialized successfully!")
            break
            
        except Exception as e:
            logging.error(f"❌ Initialization attempt {attempt + 1} failed: {e}")
            if attempt < max_init_retries - 1:
                logging.info("⏳ Waiting 30 seconds before retry...")
                await asyncio.sleep(30)
            else:
                logging.error("❌ All initialization attempts failed!")
                return

    # Get data
    projects = content_generator.projects
    accounts = content_generator.monitored_accounts

    logging.info("✅ Bot başlatıldı ve login oldu. Ana döngü başlıyor...")
    print("✅ Bot başlatıldı ve login oldu. Ana döngü başlıyor...")

    # Main loop with error recovery
    consecutive_errors = 0
    max_consecutive_errors = 5

    while True:
        try:
            logging.info("🔄 Starting new cycle...")
            
            # Login durumunu kontrol et (sadece gerekirse)
            if not twitter.is_logged_in:
                logging.info("🔍 Checking login status before cycle...")
                if not await twitter.quick_login_check():
                    logging.warning("⚠️ Login lost, attempting re-login...")
                    if not await twitter.login():
                        logging.error("❌ Re-login failed, skipping cycle")
                        await asyncio.sleep(300)  # 5 dakika bekle
                        continue
            
            # 1. Post project content
            try:
                selected_projects = random.sample(content_generator.projects, 2)
                
                for i, project in enumerate(selected_projects):
                    try:
                        logging.info(f"📝 Generating content for project {i+1}: {project['name']}")
                        content = await content_generator.generate_project_content(project)
                        
                        if content and isinstance(content, list) and len(content) > 0:
                            logging.info(f"✅ Generated {len(content)} tweets for {project['name']}")
                            if await twitter.post_thread(content):
                                logging.info(f"✅ Thread posted for {project['name']}")
                            else:
                                logging.error(f"❌ Failed to post thread for {project['name']}")
                            
                            # Wait between posts
                            await asyncio.sleep(random.uniform(60, 120))
                        else:
                            logging.warning(f"⚠️ No valid content generated for {project['name']}")
                            
                    except Exception as e:
                        logging.error(f"❌ Error with project {project['name']}: {e}")
                        continue
                        
            except Exception as e:
                logging.error(f"❌ Error in project posting: {e}")

            # 2. Reply to monitored accounts
            try:
                reply_count = 0
                max_replies_per_cycle = 3
                
                # Shuffle accounts for variety
                shuffled_accounts = random.sample(accounts, min(10, len(accounts)))
                
                for account in shuffled_accounts:
                    try:
                        if reply_count >= max_replies_per_cycle:
                            break
                        
                        logging.info(f"🔍 Checking @{account}...")
                        
                        # Get latest tweet data
                        tweet_data = await twitter.get_latest_tweet(account)
                        if not tweet_data:
                            logging.warning(f"⚠️ No tweet found for @{account}")
                            continue
                        
                        # Check if tweet is recent (within 1 hour)
                        if tweet_data.get('time'):
                            try:
                                tweet_time = datetime.fromisoformat(tweet_data['time'].replace('Z', '+00:00'))
                                time_diff = (datetime.now() - tweet_time).total_seconds()
                                
                                if time_diff <= 3600:  # 1 hour
                                    logging.info(f"✅ Recent tweet found ({time_diff/60:.1f} min ago)")
                                    
                                    reply = await content_generator.generate_reply({
                                        'text': tweet_data['text'], 
                                        'username': account
                                    })
                                    
                                    if reply and isinstance(reply, str):
                                        if await twitter.reply_to_latest_tweet(account, reply):
                                            reply_count += 1
                                            logging.info(f"✅ Reply posted to @{account} ({reply_count}/{max_replies_per_cycle})")
                                            await asyncio.sleep(random.uniform(90, 180))
                                        else:
                                            logging.error(f"❌ Failed to reply to @{account}")
                                    else:
                                        logging.warning(f"⚠️ No valid reply generated for @{account}")
                                else:
                                    logging.info(f"ℹ️ Tweet too old ({time_diff/3600:.1f} hours)")
                            except Exception as e:
                                logging.error(f"❌ Error processing tweet time for @{account}: {e}")
                        else:
                            logging.warning(f"⚠️ No timestamp found for @{account} tweet")
                            
                    except Exception as e:
                        logging.error(f"❌ Error processing @{account}: {e}")
                        continue
                
                logging.info(f"✅ Reply cycle completed. Posted {reply_count} replies.")
                
            except Exception as e:
                logging.error(f"❌ Error in reply cycle: {e}")

            # Reset error counter on successful cycle
            consecutive_errors = 0
            
            # Wait for next cycle
            logging.info("⏳ Waiting 2 hours for next cycle...")
            await asyncio.sleep(2 * 60 * 60)  # 2 hours
            
        except Exception as e:
            consecutive_errors += 1
            logging.error(f"❌ Main loop error ({consecutive_errors}/{max_consecutive_errors}): {e}")
            
            if consecutive_errors >= max_consecutive_errors:
                logging.error("❌ Too many consecutive errors, restarting...")
                try:
                    if twitter:
                        await twitter.close()
                except:
                    pass
                
                # Wait before restart
                await asyncio.sleep(300)  # 5 minutes
                
                # Restart the whole process
                return await main()
            else:
                # Wait and continue
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
