import os
import time
import random
import logging
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class APIKey:
    def __init__(self, provider: str, key_string: str, masked_name: str):
        self.provider = provider
        self.key_string = key_string
        self.masked_name = masked_name
        
        # State tracking
        self.requests_this_minute = 0
        self.minute_start_time = time.time()
        
        self.requests_today = 0
        self.day_start_time = time.time()
        
        self.cooldown_until = 0.0

    def record_usage(self):
        now = time.time()
        
        # Reset minute window
        if now - self.minute_start_time > 60:
            self.requests_this_minute = 0
            self.minute_start_time = now
            
        # Reset daily window
        if now - self.day_start_time > 86400:
            self.requests_today = 0
            self.day_start_time = now
            
        self.requests_this_minute += 1
        self.requests_today += 1

    def is_available(self) -> bool:
        now = time.time()
        if now < self.cooldown_until:
            return False
            
        if now - self.minute_start_time > 60:
            self.requests_this_minute = 0
            self.minute_start_time = now
            
        if now - self.day_start_time > 86400:
            self.requests_today = 0
            self.day_start_time = now

        # Stay slightly under published caps for safety
        if self.provider == "groq":
            return self.requests_this_minute < 28
        elif self.provider == "gemini":
            return self.requests_this_minute < 14 and self.requests_today < 480
        return False
        
    def trigger_cooldown(self, seconds: float = 30.0):
        self.cooldown_until = time.time() + seconds
        print(f"[KeyPool] {self.masked_name} ({self.provider}) put on cooldown for {seconds}s.")

class KeyPool:
    def __init__(self):
        self.keys: List[APIKey] = []
        self._load_keys()
        self.current_idx = 0
        
    def _load_keys(self):
        # Load from numbered environment variables
        for i in range(1, 15):
            g_key = os.getenv(f"GROQ_API_KEY_{i}")
            if g_key:
                self.keys.append(APIKey("groq", g_key, f"GROQ_{i}"))
            gem_key = os.getenv(f"GEMINI_API_KEY_{i}")
            if gem_key:
                self.keys.append(APIKey("gemini", gem_key, f"GEMINI_{i}"))
                
        # FALLBACK: If no numbered keys exist (e.g. on Render before user updates env vars), load base keys
        if not self.keys:
            base_g = os.getenv("GROQ_API_KEY")
            if base_g:
                self.keys.append(APIKey("groq", base_g, "GROQ_BASE"))
            base_gem = os.getenv("GEMINI_API_KEY")
            if base_gem:
                self.keys.append(APIKey("gemini", base_gem, "GEMINI_BASE"))
                
        # Shuffle keys initially to distribute load across workers if any
        random.shuffle(self.keys)

    def get_next_key(self, preferred_provider: Optional[str] = None) -> Optional[APIKey]:
        if not self.keys:
            return None
            
        # 1. Try to find a key matching the preferred provider
        if preferred_provider:
            start_idx = self.current_idx
            for _ in range(len(self.keys)):
                k = self.keys[self.current_idx]
                self.current_idx = (self.current_idx + 1) % len(self.keys)
                if k.provider == preferred_provider and k.is_available():
                    return k
            print(f"[KeyPool] All {preferred_provider} keys are busy/exhausted. Falling back to other providers.")

        # 2. If no preference or preferred provider is exhausted, fall back to ANY available key
        start_idx = self.current_idx
        for _ in range(len(self.keys)):
            k = self.keys[self.current_idx]
            self.current_idx = (self.current_idx + 1) % len(self.keys)
            if k.is_available():
                return k
                
        # 3. Complete exhaustion
        print("[KeyPool] CRITICAL: All API keys across all providers are currently exhausted or on cooldown!")
        return None

# Singleton instance
key_pool = KeyPool()
