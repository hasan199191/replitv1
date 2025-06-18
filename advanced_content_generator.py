import google.generativeai as genai
import random
import json
import logging
import os
import re
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
            # Fallback olarak başka modeller dene
            try:
                logging.info("Trying fallback models...")
                
                # Diğer ücretsiz modelleri dene
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
                
                raise Exception("All Gemini models failed")
                
            except Exception as fallback_error:
                logging.error(f"Fallback models also failed: {fallback_error}")
                raise
    
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
    
    def split_into_thread(self, content: str) -> List[str]:
        """Split content into tweet-sized chunks for a thread"""
        if not content:
            return []
            
        # Maximum tweet length
        MAX_LENGTH = 275  # Leave room for ellipsis when needed
        
        # If content fits in one tweet, return it
        if len(content) <= MAX_LENGTH:
            return [content]
            
        # Split into sentences first
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        threads = []
        current_tweet = ""
        
        for sentence in sentences:
            # If adding this sentence exceeds tweet limit
            if len(current_tweet) + len(sentence) + 2 > MAX_LENGTH:
                if current_tweet:
                    threads.append(current_tweet.strip())
                current_tweet = sentence + ". "
            else:
                current_tweet += sentence + ". "
        
        if current_tweet:
            threads.append(current_tweet.strip())
            
        # Add thread numbering if more than one tweet
        if len(threads) > 1:
            for i in range(len(threads)):
                threads[i] = f"{i+1}/{len(threads)} {threads[i]}"
                
            # Ensure no tweet exceeds limit after adding numbers
            for i in range(len(threads)):
                if len(threads[i]) > 280:
                    threads[i] = threads[i][:277] + "..."
                    
        return threads

    async def generate_project_content(self, project: Dict) -> Optional[List[str]]:
        """Generate analytical content for a project - RETURNS LIST FOR THREAD"""
        try:
            current_date = datetime.now().strftime("%B %d, %Y")
            market_context = random.choice(self.market_contexts)
            
            prompt = f"""
            You are a respected Web3 analyst with 5+ years in crypto markets. You're known for insightful takes that cut through the noise.
            
            Project Analysis:
            - Name: {project['name']}
            - Category: {project.get('category', 'Web3 Project')}
            - Twitter: {project['twitter']}
            - Current market context: {market_context}
            - Date: {current_date}
            
            Create a 2-3 tweet thread about this project. Each tweet should be under 270 characters.
            
            Structure:
            1. First tweet: Hook + key insight about the project
            2. Second tweet: Technical analysis or market positioning
            3. Third tweet (if needed): Forward-looking perspective + hashtags
            
            Writing style:
            - Analytical, not hype
            - Use specific terminology
            - Reference broader Web3 trends
            - Include 1-2 relevant hashtags only in the last tweet
            - Avoid words like "revolutionary", "game-changing"
            - Use phrases like "worth noting", "interesting development"
            
            Return ONLY the tweet texts, one per line, no numbering or formatting.
            """
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                content = response.text.strip()
                
                # Clean up formatting
                if content.startswith('"') and content.endswith('"'):
                    content = content[1:-1]
                
                # Split into lines and clean up
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                
                # Remove any JSON formatting or numbering
                cleaned_lines = []
                for line in lines:
                    # Remove JSON/array formatting
                    line = line.strip('[]"\'')
                    # Remove numeric prefixes like "1.", "2.", etc.
                    line = re.sub(r'^\d+\.\s*', '', line)
                    # Remove "Tweet X:" prefixes
                    line = re.sub(r'^Tweet\s*\d+:\s*', '', line, flags=re.IGNORECASE)
                    if line and len(line) > 10:  # Minimum meaningful content
                        cleaned_lines.append(line)
                
                # Ensure each tweet fits character limit
                final_tweets = []
                for tweet in cleaned_lines:
                    if len(tweet) > 280:
                        tweet = tweet[:277] + "..."
                    final_tweets.append(tweet)
                
                # Limit to maximum 3 tweets
                final_tweets = final_tweets[:3]
                
                if final_tweets:
                    logging.info(f"Generated thread with {len(final_tweets)} tweets for: {project['name']}")
                    for i, tweet in enumerate(final_tweets):
                        logging.info(f"Tweet {i+1}: {tweet}")
                    return final_tweets
                else:
                    logging.error(f"Failed to create valid thread for: {project['name']}")
                    return None
            else:
                logging.error(f"Failed to generate content for: {project['name']}")
                return None
                
        except Exception as e:
            logging.error(f"Error generating project content: {e}")
            return None
    
    async def generate_reply(self, tweet_data: Dict) -> Optional[str]:
        """Generate analytical reply to a tweet - RETURNS STRING"""
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
            You are a seasoned Web3 researcher engaging in a Twitter discussion. You're known for thoughtful, analytical responses.
            
            Tweet Context:
            - Author: @{username}
            - Content: "{tweet_text}"
            - Detected topics: {', '.join(found_keywords) if found_keywords else 'General Web3/crypto'}
            - Category: {tweet_category}
            
            Create a valuable reply that:
            - Provides unique insight or perspective
            - References specific protocols/metrics when relevant
            - Uses technical terminology naturally
            - Avoids generic responses
            - Is genuinely helpful to the conversation
            
            Maximum 270 characters. Return ONLY the reply text, no quotes or formatting.
            """
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                reply = response.text.strip()
                
                # Clean formatting
                if reply.startswith('"') and reply.endswith('"'):
                    reply = reply[1:-1]
                
                # Remove any prefixes
                reply = re.sub(r'^Reply:\s*', '', reply, flags=re.IGNORECASE)
                reply = re.sub(r'^Response:\s*', '', reply, flags=re.IGNORECASE)
                
                # Ensure character limit
                if len(reply) > 280:
                    reply = reply[:277] + "..."
                
                if len(reply) > 10:  # Minimum meaningful content
                    logging.info(f"Generated reply for @{username}: {reply}")
                    return reply
                else:
                    logging.error(f"Reply too short for @{username}")
                    return None
            else:
                logging.error(f"Failed to generate reply for @{username}")
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
    
    def split_content_by_sentences(self, content, char_limit=250):
        """İçeriği cümle bazında böl"""
        try:
            # Single paragraph
            content = content.replace('\n', ' ').strip()
            
            # Split by sentences
            import re
            sentences = re.split(r'(?<=[.!?])\s+', content)
            
            tweets = []
            current_tweet = ""
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                # Can we add this sentence?
                test_tweet = current_tweet + (" " if current_tweet else "") + sentence
                
                if len(test_tweet) <= char_limit:
                    current_tweet = test_tweet
                else:
                    # Save current tweet
                    if current_tweet:
                        tweets.append(current_tweet.strip())
                    # Start new tweet
                    current_tweet = sentence
            
            # Add last tweet
            if current_tweet:
                tweets.append(current_tweet.strip())
            
            return tweets
            
        except Exception as e:
            logging.error(f"Error splitting content: {e}")
            return [content[:char_limit]]
