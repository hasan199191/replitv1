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
import threading
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
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class TwitterBot:
    def __init__(self):
        self.initialization_attempts = 0
        self.max_init_attempts = 3
        self.bot_start_time = datetime.now()
        self.content_generator = AdvancedContentGenerator()
        self.email_handler = EmailHandler()
        self.browser = None
        self.last_workflow_time = 0
        self.workflow_interval = 1800  # 30 dakika
        self.tasks_started = False
        
        # Health server'ı başlat
        if os.environ.get('IS_RENDER'):
            start_health_server()
            logging.info("🏥 Health server started for Render.com")
        
        # Veri listelerini yükle
        self.load_data()
        
    def load_data(self):
        """Proje ve hesap listelerini yükle"""
        self.projects = [
            {"name": "Allora", "twitter": "@AlloraNetwork", "website": "allora.network", "category": "AI + Blockchain"},
            {"name": "Caldera", "twitter": "@Calderaxyz", "website": "caldera.xyz", "category": "Rollup Infrastructure"},
            {"name": "Camp Network", "twitter": "@campnetworkxyz", "website": "campnetwork.xyz", "category": "Social Layer"},
            {"name": "Eclipse", "twitter": "@EclipseFND", "website": "eclipse.builders", "category": "SVM L2"},
            {"name": "Fogo", "twitter": "@FogoChain", "website": "fogo.io", "category": "Gaming Chain"},
            {"name": "Humanity Protocol", "twitter": "@Humanityprot", "website": "humanity.org", "category": "Identity"},
            {"name": "Hyperbolic", "twitter": "@hyperbolic_labs", "website": "hyperbolic.xyz", "category": "AI Infrastructure"},
            {"name": "Infinex", "twitter": "@infinex", "website": "infinex.xyz", "category": "DeFi Frontend"},
            {"name": "Irys", "twitter": "@irys_xyz", "website": "irys.xyz", "category": "Data Storage"},
            {"name": "Katana", "twitter": "@KatanaRIPNet", "website": "katana.network", "category": "Gaming Infrastructure"},
            {"name": "Lombard", "twitter": "@Lombard_Finance", "website": "lombard.finance", "category": "Bitcoin DeFi"},
            {"name": "MegaETH", "twitter": "@megaeth_labs", "website": "megaeth.com", "category": "High-Performance L2"},
            {"name": "Mira Network", "twitter": "@mira_network", "website": "mira.network", "category": "Cross-Chain"},
            {"name": "Mitosis", "twitter": "@MitosisOrg", "website": "mitosis.org", "category": "Ecosystem Expansion"},
            {"name": "Monad", "twitter": "@monad_xyz", "website": "monad.xyz", "category": "Parallel EVM"},
            {"name": "Multibank", "twitter": "@multibank_io", "website": "multibank.io", "category": "Multi-Chain Banking"},
            {"name": "Multipli", "twitter": "@multiplifi", "website": "multipli.fi", "category": "Yield Optimization"},
            {"name": "Newton", "twitter": "@MagicNewton", "website": "newton.xyz", "category": "Cross-Chain Liquidity"},
            {"name": "Novastro", "twitter": "@Novastro_xyz", "website": "novastro.xyz", "category": "Cosmos DeFi"},
            {"name": "Noya.ai", "twitter": "@NetworkNoya", "website": "noya.ai", "category": "AI-Powered DeFi"},
            {"name": "OpenLedger", "twitter": "@OpenledgerHQ", "website": "openledger.xyz", "category": "Institutional DeFi"},
            {"name": "PARADEX", "twitter": "@tradeparadex", "website": "paradex.trade", "category": "Perpetuals DEX"},
            {"name": "Portal to BTC", "twitter": "@PortaltoBitcoin", "website": "portaltobitcoin.com", "category": "Bitcoin Bridge"},
            {"name": "Puffpaw", "twitter": "@puffpaw_xyz", "website": "puffpaw.xyz", "category": "Gaming + NFT"},
            {"name": "SatLayer", "twitter": "@satlayer", "website": "satlayer.xyz", "category": "Bitcoin L2"},
            {"name": "Sidekick", "twitter": "@Sidekick_Labs", "website": "N/A", "category": "Developer Tools"},
            {"name": "Somnia", "twitter": "@Somnia_Network", "website": "somnia.network", "category": "Virtual Society"},
            {"name": "Soul Protocol", "twitter": "@DigitalSoulPro", "website": "digitalsoulprotocol.com", "category": "Digital Identity"},
            {"name": "Succinct", "twitter": "@succinctlabs", "website": "succinct.xyz", "category": "Zero-Knowledge"},
            {"name": "Symphony", "twitter": "@SymphonyFinance", "website": "app.symphony.finance", "category": "Yield Farming"},
            {"name": "Theoriq", "twitter": "@theoriq_ai", "website": "theoriq.ai", "category": "AI Agents"},
            {"name": "Thrive Protocol", "twitter": "@thriveprotocol", "website": "thriveprotocol.com", "category": "Social DeFi"},
            {"name": "Union", "twitter": "@union_build", "website": "union.build", "category": "Cross-Chain Infrastructure"},
            {"name": "YEET", "twitter": "@yeet", "website": "yeet.com", "category": "Meme + Utility"}
        ]
        
        self.monitored_accounts = [
            "0x_ultra", "0xBreadguy", "beast_ico", "mdudas", "lex_node", 
            "jessepollak", "0xWenMoon", "ThinkingUSD", "udiWertheimer", 
            "vohvohh", "NTmoney", "0xMert_", "QwQiao", "DefiIgnas", 
            "notthreadguy", "Chilearmy123", "Punk9277", "DeeZe", "stevenyuntcap",
            "chefcryptoz", "ViktorBunin", "ayyyeandy", "andy8052", "Phineas_Sol",
            "MoonOverlord", "NarwhalTan", "theunipcs", "RyanWatkins_", 
            "aixbt_agent", "ai_9684xtpa", "icebergy_", "Luyaoyuan1", 
            "stacy_muur", "TheOneandOmsy", "jeffthedunker", "JoshuaDeuk", 
            "0x_scientist", "inversebrah", "dachshundwizard", "gammichan",
            "sandeepnailwal", "segall_max", "blknoiz06", "0xmons", "hosseeb",
            "GwartyGwart", "JasonYanowitz", "Tyler_Did_It", "laurashin",
            "Dogetoshi", "benbybit", "MacroCRG", "Melt_Dem"
        ]
        
        logging.info(f"Data loaded: {len(self.projects)} projects, {len(self.monitored_accounts)} accounts")
        return True
        
    async def restart_browser_if_needed(self):
        """Restart browser if it's having issues"""
        try:
            if self.browser:
                # Test if browser is responsive
                try:
                    await self.browser.page.evaluate('1 + 1')
                    return True
                except Exception as e:
                    if "crashed" in str(e).lower() or "closed" in str(e).lower():
                        logging.warning("🔄 Browser issues detected, restarting...")
                        
                        # Close current browser
                        try:
                            await self.browser.close()
                        except:
                            pass
                        
                        # Reinitialize browser
                        self.browser = TwitterBrowser()
                        if await self.browser.initialize():
                            if await self.browser.login():
                                logging.info("✅ Browser restarted successfully")
                                return True
                        
                        logging.error("❌ Browser restart failed")
                        return False
            return True
        except Exception as e:
            logging.error(f"❌ Error in browser restart: {e}")
            return False
        
    async def initialize(self):
        self.initialization_attempts += 1
        logging.info(f"🤖 Initializing Twitter Bot (Attempt {self.initialization_attempts}/{self.max_init_attempts})...")
        logging.info(f"🕐 Bot start time: {self.bot_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize content generator
        if not await self.content_generator.initialize():
            return False
            
        logging.info("🧠 Content generator initialized")
        
        # Gmail App Password kontrolü
        gmail_password = os.environ.get('GMAIL_APP_PASSWORD')
        if gmail_password:
            logging.info(f"🔐 Using Gmail App Password (length: {len(gmail_password)})")
        else:
            logging.warning("⚠️ No Gmail App Password found")
        
        # Initialize browser
        self.browser = TwitterBrowser()
        
        if not await self.browser.initialize():
            return False
            
        # Login
        if not await self.browser.login():
            logging.error("❌ Login failed")
            return False
            
        logging.info("🎉 Bot successfully initialized!")
        logging.info("📱 Session management active - minimal login attempts!")
        return True
        
    async def post_web3_projects(self):
        """2 rastgele Web3 projesi hakkında tweet gönder"""
        try:
            logging.info("🚀 Selecting and posting Web3 project content...")
        
            # 2 rastgele proje seç
            selected_projects = random.sample(self.projects, 2)
            project_names = [p['name'] for p in selected_projects]
            logging.info(f"📋 Selected projects: {project_names}")
        
            success_count = 0
        
            for i, project in enumerate(selected_projects):
                try:
                    logging.info(f"📝 Processing project {i+1}/2: {project['name']}")
                
                    # İçerik oluştur
                    content = await self.content_generator.generate_project_content(project)
                
                    if content:
                        # İçerik 280 karakterden uzunsa thread olarak gönder
                        if len(content) > 280:
                            # İçeriği parçalara böl
                            content_parts = []
                            words = content.split()
                            current_part = ""
                        
                            for word in words:
                                if len(current_part + " " + word) <= 275:  # 5 karakter margin
                                    current_part += " " + word if current_part else word
                                else:
                                    if current_part:
                                        content_parts.append(current_part)
                                    current_part = word
                        
                            if current_part:
                                content_parts.append(current_part)
                        
                            logging.info(f"📝 Content split into {len(content_parts)} parts")
                        
                            # Thread olarak gönder
                            if await self.browser.post_tweet_thread(content_parts):
                                logging.info(f"✅ Successfully posted thread for {project['name']}")
                                success_count += 1
                            else:
                                logging.error(f"❌ Failed to post thread for {project['name']}")
                        else:
                            # Tek tweet olarak gönder
                            if await self.browser.post_tweet(content):
                                logging.info(f"✅ Successfully posted content for {project['name']}")
                                success_count += 1
                            else:
                                logging.error(f"❌ Failed to post content for {project['name']}")
                    else:
                        logging.error(f"❌ Failed to generate content for {project['name']}")
                
                    # Projeler arası bekleme
                    if i < len(selected_projects) - 1:
                        wait_time = random.uniform(30, 60)
                        logging.info(f"⏳ Waiting {wait_time:.1f} seconds before next project...")
                        await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    logging.error(f"❌ Error processing project {project['name']}: {e}")
                    continue
        
            logging.info(f"📊 Project posting completed: {success_count}/2 successful")
            return success_count > 0
        
        except Exception as e:
            logging.error(f"❌ Error in post_web3_projects: {e}")
            return False
            
    async def reply_to_monitored_accounts(self):
        """Takip edilen hesapların tweetlerine cevap ver"""
        try:
            logging.info("💬 Starting reply task for monitored accounts...")
        
            # 3 rastgele hesap seç
            selected_accounts = random.sample(self.monitored_accounts, 3)
            logging.info(f"👥 Selected accounts: {selected_accounts}")
        
            success_count = 0
        
            for account in selected_accounts:
                try:
                    logging.info(f"🔍 Processing @{account}...")
                
                    # Son tweetleri al (son 1 saat içindeki)
                    recent_tweets = await self.browser.get_user_recent_tweets(account, limit=3)
                
                    if recent_tweets:
                        # En son tweet'e cevap ver
                        latest_tweet = recent_tweets[0]
                    
                        # Cevap içeriği oluştur
                        reply_content = await self.content_generator.generate_reply(latest_tweet)
                    
                        if reply_content:
                            # Cevap gönder
                            if await self.browser.reply_to_tweet(latest_tweet['url'], reply_content):
                                logging.info(f"✅ Successfully replied to @{account}")
                                success_count += 1
                            else:
                                logging.error(f"❌ Failed to reply to @{account}")
                        else:
                            logging.error(f"❌ Failed to generate reply for @{account}")
                    else:
                        logging.warning(f"⚠️ No recent tweets found for @{account}")
                
                    # Hesaplar arası bekleme
                    wait_time = random.uniform(15, 30)
                    logging.info(f"⏳ Waiting {wait_time:.1f} seconds before next account...")
                    await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    logging.error(f"❌ Error processing @{account}: {e}")
                    continue
        
            logging.info(f"📊 Reply task completed: {success_count}/3 successful")
            return success_count > 0
        
        except Exception as e:
            logging.error(f"❌ Error in reply_to_monitored_accounts: {e}")
            return False
            
    async def run_complete_workflow(self):
        """Tam workflow'u çalıştır"""
        try:
            logging.info("🔄 Starting COMPLETE workflow...")
            logging.info(f"🕐 Workflow start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Login kontrolü
            if not await self.browser.check_login_status():
                logging.info("🔐 Login required, attempting to login...")
                if not await self.browser.login():
                    logging.error("❌ Login failed, skipping workflow")
                    return False
            
            # Browser health check
            if not await self.restart_browser_if_needed():
                logging.error("❌ Browser restart failed, skipping workflow")
                return False
            
            workflow_success = True
            
            # TASK 1: Web3 proje içeriği paylaş
            logging.info("📋 TASK 1: Posting Web3 project content...")
            task1_success = await self.post_web3_projects()
            if not task1_success:
                workflow_success = False
            
            # Görevler arası bekleme
            logging.info("⏳ Waiting 2 minutes between tasks...")
            await asyncio.sleep(120)
            
            # TASK 2: Monitored accounts'lara cevap ver
            logging.info("📋 TASK 2: Replying to monitored accounts...")
            task2_success = await self.reply_to_monitored_accounts()
            if not task2_success:
                workflow_success = False
            
            # Workflow tamamlandı
            self.last_workflow_time = time.time()
            
            if workflow_success:
                logging.info("🎉 COMPLETE workflow finished successfully!")
            else:
                logging.warning("⚠️ COMPLETE workflow finished with some errors")
            
            return workflow_success
            
        except Exception as e:
            logging.error(f"❌ Error in complete workflow: {e}")
            return False
    
    async def run(self):
        while self.initialization_attempts < self.max_init_attempts:
            if await self.initialize():
                logging.info("🤖 Twitter Bot is now running!")
                logging.info("📋 Task 1: Post 2 Web3 projects")
                logging.info("💬 Task 2: Reply to monitored accounts")
                logging.info("🛡️ Anti-detection measures active")
                logging.info("📱 Persistent session with minimal login attempts")
                logging.info(f"🚀 Projects available: {len(self.projects)}")
                logging.info(f"👥 Monitored accounts: {len(self.monitored_accounts)}")
                
                # Ana bot döngüsü
                try:
                    # İlk workflow'u hemen başlat
                    logging.info("🚀 Starting initial COMPLETE workflow NOW...")
                    await self.run_complete_workflow()
                    
                    # Ana döngü
                    while True:
                        current_time = time.time()
                        time_since_last = current_time - self.last_workflow_time
                        
                        if time_since_last >= self.workflow_interval:
                            logging.info("🔄 30 minutes passed, starting new workflow...")
                            await self.run_complete_workflow()
                        else:
                            remaining_time = self.workflow_interval - time_since_last
                            remaining_minutes = remaining_time / 60
                            logging.info(f"⏰ Next workflow in {remaining_minutes:.1f} minutes")
                        
                        # 5 dakika bekle
                        await asyncio.sleep(300)
                        
                except KeyboardInterrupt:
                    logging.info("🛑 Bot stopped by user")
                    break
                    
            else:
                if self.initialization_attempts >= self.max_init_attempts:
                    logging.error(f"❌ Failed to initialize after {self.max_init_attempts} attempts")
                    break
                else:
                    logging.warning(f"⚠️ Initialization failed, retrying in 30 seconds...")
                    await asyncio.sleep(30)
                    
        # Cleanup
        if self.browser:
            await self.browser.close()

async def main():
    bot = TwitterBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
