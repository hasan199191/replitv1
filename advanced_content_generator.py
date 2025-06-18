import google.generativeai as genai
import random
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional

class AdvancedContentGenerator:
    def __init__(self):
        self.model = None
        self.api_key = None
        self.projects = []
        self.monitored_accounts = []
        self.keywords = []
        self.market_contexts = [
            "bull market momentum",
            "bear market resilience", 
            "institutional adoption",
            "regulatory clarity",
            "technical innovation",
            "ecosystem growth",
            "user adoption metrics",
            "TVL growth",
            "cross-chain integration",
            "scalability solutions"
        ]
        
    async def initialize(self):
        """Initialize Gemini AI with Flash 2.0"""
        try:
            self.api_key = os.environ.get('GEMINI_API_KEY')
        
            if not self.api_key:
                raise Exception("Gemini API key not found")
        
            genai.configure(api_key=self.api_key)
        
            # Gemini Flash 2.0 modelini kullan (ücretsiz)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
            self.load_data()
        
            logging.info("Advanced Gemini Flash 2.0 and data lists successfully initialized")
            return True
        
        except Exception as e:
            logging.error(f"Error initializing Gemini Flash 2.0: {e}")
            # Fallback olarak başka modelleri dene
            try:
                logging.info("Trying fallback models...")
            
                fallback_models = [
                    'gemini-1.5-flash',
                    'gemini-1.5-flash-latest',
                    'gemini-flash'
                ]
            
                for model_name in fallback_models:
                    try:
                        self.model = genai.GenerativeModel(model_name)
                        # Test et
                        test_response = self.model.generate_content("Test")
                        if test_response.text:
                            logging.info(f"Successfully initialized with {model_name}")
                            self.load_data()
                            return True
                    except Exception as model_error:
                        logging.warning(f"Model {model_name} failed: {model_error}")
                        continue
            
            # Son çare olarak sync versiyonu dene
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.load_data()
            logging.info("Initialized with basic Gemini model")
            return True
            
        except Exception as fallback_error:
            logging.error(f"All Gemini models failed: {fallback_error}")
            return False
    
    def load_data(self):
        """Load project and account lists"""
        # Projects
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
        
        # Monitored accounts
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
        
        # Keywords
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
            "XION", "YEET", "Zcash", "DeFi", "NFT", "Web3", "Layer2", "zkSync",
            "Ethereum", "Bitcoin", "Solana", "Polygon", "Avalanche", "Cosmos"
        ]
        
        logging.info(f"Data loaded: {len(self.projects)} projects, {len(self.monitored_accounts)} accounts")
    
    def select_random_projects(self, count: int = 2) -> List[Dict]:
        """Select random projects"""
        if len(self.projects) <= count:
            return self.projects
        return random.sample(self.projects, count)
    
    def get_random_accounts(self, count: int = 5) -> List[str]:
        """Select random accounts"""
        if len(self.monitored_accounts) <= count:
            return self.monitored_accounts
        return random.sample(self.monitored_accounts, count)
    
    async def generate_project_content(self, project: Dict) -> Optional[str]:
        """Generate analytical content for a project"""
        try:
            current_date = datetime.now().strftime("%B %d, %Y")
            market_context = random.choice(self.market_contexts)
            
            prompt = f"""
You are a Web3 analyst creating a Twitter post. CRITICAL: Maximum 250 characters total.

Project: {project['name']} ({project['twitter']})
Category: {project.get('category', 'Web3 Project')}

STRICT RULES:
- MAXIMUM 250 characters (including spaces, hashtags, handles)
- MUST include the project's Twitter handle {project['twitter']}
- Write in English only
- No prefixes like "Tweet 1:" or numbering
- Be analytical and insightful
- Use 1-2 hashtags maximum
- Focus on ONE key insight about the project

Format: Direct insight + project handle + 1-2 hashtags

Example good format:
"[Insight about project] {project['twitter']} [brief technical detail] #DeFi #Web3"

Write the tweet now (under 250 characters):
"""
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                content = response.text.strip()
                # Clean up formatting
                if content.startswith('"') and content.endswith('"'):
                    content = content[1:-1]
                
                # Remove "Tweet X:" prefixes
                import re
                content = re.sub(r'^Tweet \d+:\s*', '', content)
                content = re.sub(r'\s*Tweet \d+:\s*', ' ', content)
                
                # STRICT character limit check
                if len(content) > 270:
                    content = content[:267] + "..."
                    logging.warning(f"Content truncated to fit character limit: {len(content)} chars")
                
                logging.info(f"Content generated ({len(content)} chars): {content}")
                return content
            else:
                logging.error(f"Failed to generate content for: {project['name']}")
                return None
                
        except Exception as e:
            logging.error(f"Error generating project content: {e}")
            return None
    
    async def generate_reply(self, tweet_data: Dict) -> Optional[str]:
        """Generate analytical reply to a tweet"""
        try:
            tweet_text = tweet_data.get('text', '')
            username = tweet_data.get('username', '')
            
            # Analyze tweet for Web3 topics
            found_keywords = []
            for keyword in self.keywords:
                if keyword.lower() in tweet_text.lower():
                    found_keywords.append(keyword)
            
            # Determine tweet category
            tweet_category = self.categorize_tweet(tweet_text, found_keywords)
            
            prompt = f"""
            You are a seasoned Web3 researcher engaging in a Twitter discussion. You're known for thoughtful, analytical responses that add genuine value.
            
            Tweet Context:
            - Author: @{username} (crypto/Web3 influencer)
            - Content: "{tweet_text}"
            - Detected topics: {', '.join(found_keywords) if found_keywords else 'General Web3/crypto'}
            - Category: {tweet_category}
            
            Your expertise areas:
            - DeFi protocols and yield strategies
            - Layer 1/Layer 2 scaling solutions  
            - NFT market dynamics and utility
            - Cross-chain infrastructure
            - Tokenomics and governance
            - Market analysis and trends
            
            Response guidelines:
            - Provide a unique perspective or insight
            - Reference specific protocols, metrics, or trends when relevant
            - Ask a thoughtful follow-up question if appropriate
            - Share a contrarian view if you disagree (respectfully)
            - Use technical terminology naturally
            - Avoid generic responses like "great point" or "thanks for sharing"
            - Don't be promotional or salesy
            
            Response types to consider:
            - Technical clarification or additional context
            - Market data or trend observation  
            - Comparison to similar projects/situations
            - Historical precedent or pattern recognition
            - Risk assessment or consideration
            - Implementation challenge or opportunity
            
            Maximum 280 characters. Respond as if you're genuinely interested in advancing the conversation.
            """
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                reply = response.text.strip()
                if reply.startswith('"') and reply.endswith('"'):
                    reply = reply[1:-1]
                
                if len(reply) > 280:
                    reply = reply[:277] + "..."
                
                logging.info(f"Advanced reply generated for: @{username}")
                return reply
            else:
                logging.error(f"Failed to generate reply for: @{username}")
                return None
                
        except Exception as e:
            logging.error(f"Error generating reply: {e}")
            return None
    
    def categorize_tweet(self, tweet_text: str, keywords: List[str]) -> str:
        """Categorize tweet based on content"""
        text_lower = tweet_text.lower()
        
        if any(word in text_lower for word in ['defi', 'yield', 'liquidity', 'tvl', 'apy']):
            return "DeFi Discussion"
        elif any(word in text_lower for word in ['nft', 'opensea', 'mint', 'collection']):
            return "NFT Discussion"  
        elif any(word in text_lower for word in ['layer2', 'l2', 'scaling', 'rollup']):
            return "Scaling Solutions"
        elif any(word in text_lower for word in ['bitcoin', 'btc', 'ethereum', 'eth']):
            return "Major Crypto Assets"
        elif any(word in text_lower for word in ['ai', 'artificial intelligence', 'machine learning']):
            return "AI + Crypto"
        elif any(word in text_lower for word in ['regulation', 'sec', 'compliance']):
            return "Regulatory Discussion"
        elif any(word in text_lower for word in ['gaming', 'metaverse', 'virtual']):
            return "Gaming/Metaverse"
        else:
            return "General Web3"
    
    async def generate_market_insight(self) -> Optional[str]:
        """Generate general market insight tweet"""
        try:
            market_context = random.choice(self.market_contexts)
            
            prompt = f"""
            You are a crypto market analyst sharing a weekly insight with your followers. Current focus: {market_context}
            
            Create an insightful tweet about the current Web3/crypto landscape that:
            - Identifies an underappreciated trend or pattern
            - Provides actionable perspective for builders or investors  
            - References specific metrics, protocols, or developments
            - Avoids generic market commentary
            - Shows deep understanding of the space
            
            Topics to potentially explore:
            - Cross-chain infrastructure maturation
            - DeFi yield landscape evolution
            - Layer 2 adoption metrics
            - Institutional crypto adoption signals
            - Developer activity trends
            - Regulatory clarity impact
            - NFT utility evolution beyond art
            
            Maximum 280 characters. Write as if you're sharing alpha that others might miss.
            """
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                content = response.text.strip()
                if content.startswith('"') and content.endswith('"'):
                    content = content[1:-1]
                
                if len(content) > 280:
                    content = content[:277] + "..."
                
                logging.info("Market insight generated")
                return content
            else:
                logging.error("Failed to generate market insight")
                return None
                
        except Exception as e:
            logging.error(f"Error generating market insight: {e}")
            return None
