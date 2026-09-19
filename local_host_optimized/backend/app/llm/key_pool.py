import os
import time
import asyncio
import logging
import random
from typing import Optional, List, Callable, Awaitable

logger = logging.getLogger(__name__)

class APIKey:
    def __init__(self, provider: str, key_string: str, masked_name: str):
        self.provider = provider
        self.key_string = key_string
        self.masked_name = masked_name
        self.cooldown_until = 0.0

    def is_available(self) -> bool:
        return time.time() >= self.cooldown_until
        
    def trigger_cooldown(self, seconds: float = 30.0):
        self.cooldown_until = time.time() + seconds

class KeyPool:
    def __init__(self):
        self.keys: List[APIKey] = []
        self.current_idx = 0
        
    def load_keys_from_env(self):
        self.keys.clear()
        
        for i in range(1, 15):
            g_key = os.getenv(f"GROQ_API_KEY_{i}")
            if g_key:
                self.keys.append(APIKey("groq", g_key, f"GROQ_{i}"))
            gem_key = os.getenv(f"GEMINI_API_KEY_{i}")
            if gem_key:
                self.keys.append(APIKey("gemini", gem_key, f"GEMINI_{i}"))
                
        if not self.keys:
            base_g = os.getenv("GROQ_API_KEY")
            if base_g:
                self.keys.append(APIKey("groq", base_g, "GROQ_BASE"))
            base_gem = os.getenv("GEMINI_API_KEY")
            if base_gem:
                self.keys.append(APIKey("gemini", base_gem, "GEMINI_BASE"))
                
        random.shuffle(self.keys)

    def _get_next_key(self, prefer_provider: Optional[str] = None) -> Optional[APIKey]:
        if not self.keys:
            return None
            
        if prefer_provider:
            start_idx = self.current_idx
            for _ in range(len(self.keys)):
                k = self.keys[self.current_idx]
                self.current_idx = (self.current_idx + 1) % len(self.keys)
                if k.provider == prefer_provider and k.is_available():
                    return k
                    
        start_idx = self.current_idx
        for _ in range(len(self.keys)):
            k = self.keys[self.current_idx]
            self.current_idx = (self.current_idx + 1) % len(self.keys)
            if k.is_available():
                return k
                
        return None

    async def execute(
        self, 
        operation: Callable[[str, str], Awaitable[str]], 
        prefer_provider: Optional[str] = None, 
        max_rounds: int = 4
    ) -> str:
        
        for attempt in range(max_rounds):
            key_obj = self._get_next_key(prefer_provider)
            if not key_obj:
                # All keys busy, wait and retry
                await asyncio.sleep(2)
                continue
                
            try:
                # Execute the wrapped operation
                result = await operation(key_obj.provider, key_obj.key_string)
                return result
            except Exception as e:
                # Check for rate limit / 429
                err_str = str(e).lower()
                if "429" in err_str or "rate limit" in err_str or "401" in err_str or "404" in err_str or "exhausted" in err_str:
                    logger.warning(f"[KeyPool] {key_obj.masked_name} hit rate limit/error. Cooling down for 30s.")
                    key_obj.trigger_cooldown(30.0)
                else:
                    logger.error(f"[KeyPool] Operation failed on {key_obj.masked_name}: {e}")
                    # If it's a structural or validation error, we still try another key just in case,
                    # but typically rate limits are what trigger cooldowns.
                
                if attempt == max_rounds - 1:
                    raise e
                
                # Switch preferred provider to load-balance failures
                prefer_provider = "groq" if prefer_provider == "gemini" else "gemini"
                
                # Jitter backoff only for retry rounds
                backoff = (2 ** attempt) + random.uniform(0.1, 0.5)
                await asyncio.sleep(backoff)
                
        raise Exception("All retry rounds exhausted in pool.execute")

pool = KeyPool()
