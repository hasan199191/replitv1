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
        self.twitter_browser = TwitterBrowser()
        self.content_generator = AdvancedContentGenerator()
        self.is_running = False
        self.health_server = None
        
    async def initialize(self):
        """Bot'u başlat ve Twitter'a bağlan"""
        try:
            # Health server'ı başlat (Render için gerekli)
            if os.environ.get('IS_RENDER'):
                self.health_server = start_health_server()
                logging.info("Health server started for Render.com")
            
            # İçerik üreticisini başlat
            await self.content_generator.initialize()
            
            # Twitter tarayıcısını başlat
            if not self.twitter_browser.initialize():
                raise Exception("Twitter browser could not be initialized")
            
            # Twitter'a giriş yap
            if not self.twitter_browser.login():
                raise Exception("Could not login to Twitter")
            
            logging.info("Bot successfully initialized")
            return True
            
        except Exception as e:
            logging.error(f"Error initializing bot: {e}")
            return False
    
    async def post_hourly_content(self):
        """Hourly content posting"""
        try:
            logging.info("Starting hourly content posting...")
            
            # Select 2 projects from the list
            selected_projects = self.content_generator.select_random_projects(2)
            
            for i, project in enumerate(selected_projects):
                try:
                    # Generate content with Gemini
                    content = await self.content_generator.generate_project_content(project)
                    
                    if content:
                        # Post to Twitter
                        success = self.twitter_browser.post_tweet(content)
                        if success:
                            logging.info(f"Content successfully posted: {project['name']}")
                        else:
                            logging.error(f"Failed to post content: {project['name']}")
                    else:
                        logging.error(f"No content generated for: {project['name']}")
                    
                    # Wait between projects (avoid rate limits)
                    if i < len(selected_projects) - 1:
                        await asyncio.sleep(45)
                        
                except Exception as e:
                    logging.error(f"Error processing project {project['name']}: {e}")
                    continue
                
        except Exception as e:
            logging.error(f"Error in hourly content posting: {e}")
    
    async def check_and_reply_to_tweets(self):
        """Check monitored accounts and reply to tweets"""
        try:
            logging.info("Checking monitored accounts for new tweets...")
            
            # Select random 5 accounts
            selected_accounts = self.content_generator.get_random_accounts(5)
            
            for i, username in enumerate(selected_accounts):
                try:
                    # Follow the user
                    self.twitter_browser.follow_user(username)
                    
                    # Get latest tweet
                    tweet_data = self.twitter_browser.get_latest_tweet(username)
                    
                    if tweet_data:
                        # Check if tweet is within last hour
                        tweet_time = datetime.fromisoformat(tweet_data['time'].replace('Z', '+00:00'))
                        now = datetime.now().astimezone()
                        
                        if now - tweet_time < timedelta(hours=1):
                            # Generate reply with Gemini
                            reply_content = await self.content_generator.generate_reply(tweet_data)
                            
                            if reply_content:
                                # Send reply
                                success = self.twitter_browser.reply_to_tweet(
                                    tweet_data['url'], 
                                    reply_content
                                )
                                
                                if success:
                                    logging.info(f"Successfully replied to @{username}")
                                else:
                                    logging.error(f"Failed to reply to @{username}")
                            else:
                                logging.error(f"No reply generated for @{username}")
                        else:
                            logging.info(f"@{username}'s latest tweet is older than 1 hour, skipping")
                    else:
                        logging.warning(f"No tweets found for @{username}")
                    
                    # Wait between accounts (avoid rate limits)
                    if i < len(selected_accounts) - 1:
                        await asyncio.sleep(90)
                    
                except Exception as e:
                    logging.error(f"Error processing @{username}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Error checking and replying to tweets: {e}")
    
    def schedule_tasks(self):
        """Schedule bot tasks"""
        # Hourly content posting
        schedule.every().hour.at(":00").do(
            lambda: asyncio.create_task(self.post_hourly_content())
        )
        
        # Hourly tweet checking and replying
        schedule.every().hour.at(":30").do(
            lambda: asyncio.create_task(self.check_and_reply_to_tweets())
        )
        
        logging.info("Tasks scheduled successfully")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        self.is_running = False
        if self.twitter_browser:
            self.twitter_browser.close()
        sys.exit(0)
    
    async def run(self):
        """Run the bot"""
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        if not await self.initialize():
            logging.error("Bot could not be initialized")
            return
        
        self.is_running = True
        self.schedule_tasks()
        
        logging.info("Bot started successfully and is running...")
        
        # Run initial content posting
        await self.post_hourly_content()
        
        # Main loop
        while self.is_running:
            try:
                schedule.run_pending()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)

async def main():
    bot = TwitterBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        # Clean shutdown
        if bot.twitter_browser:
            bot.twitter_browser.close()
        logging.info("Bot shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
