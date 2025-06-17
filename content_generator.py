import google.generativeai as genai
import random
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional

class ContentGenerator:
    def __init__(self):
        self.model = None
        self.api_key = None
        self.projects = []
        self.monitored_accounts = []
        self.keywords = []
        
    async def initialize(self):
        """Gemini AI'ı başlat"""
        try:
            # API anahtarını yükle
            self.api_key = os.environ.get('GEMINI_API_KEY')
            
            if not self.api_key:
                raise Exception("Gemini API anahtarı bulunamadı")
            
            # Gemini'yi yapılandır
            genai.configure(api_key=self.api_key)
            
            # Model oluştur
            self.model = genai.GenerativeModel('gemini-pro')
            
            # Proje ve hesap listelerini yükle
            self.load_data()
            
            logging.info("Gemini AI ve veri listeleri başarıyla başlatıldı")
            return True
            
        except Exception as e:
            logging.error(f"Gemini AI başlatılırken hata: {e}")
            raise
    
    def load_data(self):
        """Proje ve hesap listelerini yükle"""
        # Projeler
        self.projects = [
            {"name": "Allora", "twitter": "@AlloraNetwork", "website": "allora.network"},
            {"name": "Caldera", "twitter": "@Calderaxyz", "website": "caldera.xyz"},
            {"name": "Camp Network", "twitter": "@campnetworkxyz", "website": "campnetwork.xyz"},
            {"name": "Eclipse", "twitter": "@EclipseFND", "website": "eclipse.builders"},
            {"name": "Fogo", "twitter": "@FogoChain", "website": "fogo.io"},
            {"name": "Humanity Protocol", "twitter": "@Humanityprot", "website": "humanity.org"},
            {"name": "Hyperbolic", "twitter": "@hyperbolic_labs", "website": "hyperbolic.xyz"},
            {"name": "Infinex", "twitter": "@infinex", "website": "infinex.xyz"},
            {"name": "Irys", "twitter": "@irys_xyz", "website": "irys.xyz"},
            {"name": "Katana", "twitter": "@KatanaRIPNet", "website": "katana.network"},
            {"name": "Lombard", "twitter": "@Lombard_Finance", "website": "lombard.finance"},
            {"name": "MegaETH", "twitter": "@megaeth_labs", "website": "megaeth.com"},
            {"name": "Mira Network", "twitter": "@mira_network", "website": "mira.network"},
            {"name": "Mitosis", "twitter": "@MitosisOrg", "website": "mitosis.org"},
            {"name": "Monad", "twitter": "@monad_xyz", "website": "monad.xyz"},
            {"name": "Multibank", "twitter": "@multibank_io", "website": "multibank.io"},
            {"name": "Multipli", "twitter": "@multiplifi", "website": "multipli.fi"},
            {"name": "Newton", "twitter": "@MagicNewton", "website": "newton.xyz"},
            {"name": "Novastro", "twitter": "@Novastro_xyz", "website": "novastro.xyz"},
            {"name": "Noya.ai", "twitter": "@NetworkNoya", "website": "noya.ai"},
            {"name": "OpenLedger", "twitter": "@OpenledgerHQ", "website": "openledger.xyz"},
            {"name": "PARADEX", "twitter": "@tradeparadex", "website": "paradex.trade"},
            {"name": "Portal to BTC", "twitter": "@PortaltoBitcoin", "website": "portaltobitcoin.com"},
            {"name": "Puffpaw", "twitter": "@puffpaw_xyz", "website": "puffpaw.xyz"},
            {"name": "SatLayer", "twitter": "@satlayer", "website": "satlayer.xyz"},
            {"name": "Sidekick", "twitter": "@Sidekick_Labs", "website": "N/A"},
            {"name": "Somnia", "twitter": "@Somnia_Network", "website": "somnia.network"},
            {"name": "Soul Protocol", "twitter": "@DigitalSoulPro", "website": "digitalsoulprotocol.com"},
            {"name": "Succinct", "twitter": "@succinctlabs", "website": "succinct.xyz"},
            {"name": "Symphony", "twitter": "@SymphonyFinance", "website": "app.symphony.finance"},
            {"name": "Theoriq", "twitter": "@theoriq_ai", "website": "theoriq.ai"},
            {"name": "Thrive Protocol", "twitter": "@thriveprotocol", "website": "thriveprotocol.com"},
            {"name": "Union", "twitter": "@union_build", "website": "union.build"},
            {"name": "YEET", "twitter": "@yeet", "website": "yeet.com"}
        ]
        
        # Takip edilecek hesaplar
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
        
        # Anahtar kelimeler
        self.keywords = [
            "0G", "Allora", "ANIME", "Aptos", "Arbitrum", "Berachain", "Boop", 
            "Caldera", "Camp Network", "Corn", "Defi App", "dYdX", "Eclipse", 
            "Fogo", "Frax", "FUEL", "Huma", "Humanity Protocol", "Hyperbolic", 
            "Initia", "Injective", "Infinex", "IQ", "Irys", "Kaia", "Kaito", 
            "MegaETH", "Mitosis", "Monad", "Movement", "Multibank", "Multipli", 
            "Near", "Newton", "Novastro", "OpenLedger", "PARADEX", "PENGU", 
            "Polkadot", "Portal to BTC", "PuffPaw", "Pyth", "QUAI", "SatLayer", 
            "Sei", "Sidekick", "Skate", "Somnia", "Soon", "Soph Protocol", 
            "Soul Protocol", "Starknet", "Story", "Succinct", "Symphony", 
            "Theoriq", "Thrive Protocol", "Union", "Virtuals Protocol", "Wayfinder", 
            "XION", "YEET", "Zcash"
        ]
        
        logging.info(f"Veri listeleri yüklendi: {len(self.projects)} proje, {len(self.monitored_accounts)} hesap")
    
    def select_random_projects(self, count: int = 2) -> List[Dict]:
        """Rastgele proje seç"""
        if len(self.projects) <= count:
            return self.projects
        return random.sample(self.projects, count)
    
    def get_random_accounts(self, count: int = 5) -> List[str]:
        """Rastgele hesap seç"""
        if len(self.monitored_accounts) <= count:
            return self.monitored_accounts
        return random.sample(self.monitored_accounts, count)
    
    async def generate_project_content(self, project: Dict) -> Optional[str]:
        """Generate content for a project"""
        try:
            current_date = datetime.now().strftime("%B %d, %Y")
            
            prompt = f"""
        You are a seasoned Web3 analyst and crypto researcher with deep market insights. Create an engaging Twitter post about this blockchain project:
        
        Project: {project['name']}
        Twitter: {project['twitter']}
        Website: {project['website']}
        Today's Date: {current_date}
        
        Context: You're analyzing this project from multiple angles - technical innovation, market positioning, ecosystem impact, and investment potential.
        
        Requirements:
        - Maximum 280 characters
        - Write like a human analyst, not a bot
        - Include your personal take or unique insight
        - Compare to similar projects or market trends when relevant
        - Use analytical language: "interesting to note", "worth watching", "key differentiator"
        - Add 1-2 relevant hashtags naturally
        - Avoid generic phrases like "exciting project" or "revolutionary"
        - Focus on WHY this matters in the current Web3 landscape
        
        Write as if you're sharing a genuine insight with your crypto Twitter followers.
        """
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                content = response.text.strip()
                # Remove quotes if Gemini adds them
                if content.startswith('"') and content.endswith('"'):
                    content = content[1:-1]
            
                # 280 character limit check
                if len(content) > 280:
                    content = content[:277] + "..."
            
                logging.info(f"Content generated for: {project['name']}")
                return content
            else:
                logging.error(f"Failed to generate content for: {project['name']}")
                return None
            
        except Exception as e:
            logging.error(f"Error generating content: {e}")
            return None
    
    async def generate_reply(self, tweet_data: Dict) -> Optional[str]:
        """Generate reply to a tweet"""
        try:
            tweet_text = tweet_data.get('text', '')
            username = tweet_data.get('username', '')
        
            # Check for keywords
            found_keywords = []
            for keyword in self.keywords:
                if keyword.lower() in tweet_text.lower():
                    found_keywords.append(keyword)
        
            keyword_context = ""
            if found_keywords:
                keyword_context = f"Relevant Web3 topics mentioned: {', '.join(found_keywords)}"
        
            prompt = f"""
        You are a knowledgeable Web3 researcher and crypto analyst engaging in Twitter discussions. Reply to this tweet with genuine insight:
        
        Tweet Author: @{username}
        Tweet Content: "{tweet_text}"
        {keyword_context}
        
        Context: This is a crypto/Web3 discussion. You should respond as someone who:
        - Has deep knowledge of blockchain technology, DeFi, NFTs, and crypto markets
        - Provides thoughtful analysis rather than generic responses
        - Asks insightful questions or adds valuable perspective
        - References market trends, technical aspects, or ecosystem developments when relevant
        - Engages authentically, not like a promotional bot
        
        Requirements:
        - Maximum 280 characters
        - Write like a human expert, not an AI
        - Add genuine value to the conversation
        - Use analytical phrases: "interesting point about", "this reminds me of", "worth considering"
        - Reference specific Web3 concepts, protocols, or market dynamics when relevant
        - Avoid generic praise like "great post" or "thanks for sharing"
        - Don't be overly promotional or salesy
        - Ask a thoughtful follow-up question if appropriate
        
        Respond as if you're genuinely interested in the topic and want to contribute meaningfully to the discussion.
        """
        
            response = self.model.generate_content(prompt)
        
            if response.text:
                reply = response.text.strip()
                # Remove quotes if Gemini adds them
                if reply.startswith('"') and reply.endswith('"'):
                    reply = reply[1:-1]
            
                # 280 character limit check
                if len(reply) > 280:
                    reply = reply[:277] + "..."
            
                logging.info(f"Reply generated for: @{username}")
                return reply
            else:
                logging.error(f"Failed to generate reply for: @{username}")
                return None
            
        except Exception as e:
            logging.error(f"Error generating reply: {e}")
            return None
    
    async def generate_hashtags(self, content: str, max_tags: int = 3) -> List[str]:
        """İçerik için hashtag üret"""
        try:
            prompt = f"""
            Aşağıdaki içerik için uygun hashtag'ler öner:
            
            İçerik: "{content}"
            
            Gereksinimler:
            - Maksimum {max_tags} hashtag
            - Türkçe ve İngilizce karışık olabilir
            - Popüler ve alakalı hashtag'ler
            - # işareti ile başlasın
            
            Sadece hashtag'leri virgülle ayırarak döndür.
            """
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                hashtags = [tag.strip() for tag in response.text.split(',')]
                return hashtags[:max_tags]
            else:
                return []
                
        except Exception as e:
            logging.error(f"Hashtag üretilirken hata: {e}")
            return []
