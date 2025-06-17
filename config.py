import os
import json
from typing import Dict, Any

class Config:
    def __init__(self):
        self.config_file = 'data/config.json'
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Konfigürasyon dosyasını yükle"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Varsayılan config oluştur
                return self.create_default_config()
        except Exception as e:
            print(f"Config yüklenirken hata: {e}")
            return self.create_default_config()
    
    def create_default_config(self) -> Dict[str, Any]:
        """Varsayılan konfigürasyon oluştur"""
        default_config = {
            "bot_settings": {
                "post_interval_hours": 1,
                "reply_times": ["08:00", "14:00", "20:00"],
                "max_tweets_per_hour": 2,
                "max_replies_per_session": 5
            },
            "content_settings": {
                "max_tweet_length": 280,
                "include_hashtags": True,
                "max_hashtags": 3,
                "language": "tr"
            },
            "safety_settings": {
                "rate_limit_delay": 60,
                "error_retry_count": 3,
                "backup_enabled": True
            }
        }
        
        # Config dosyasını kaydet
        os.makedirs('data', exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        return default_config
    
    def get(self, key: str, default=None):
        """Config değeri al"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def update(self, key: str, value: Any):
        """Config değeri güncelle"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        
        # Dosyayı güncelle
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
