
from __future__ import annotations

from enum import Enum


class FallbackLevel(Enum):
    L1 = "MODEL_FALLBACK"
    L2 = "PARALLEL_FALLBACK"
    L3 = "CACHE_FALLBACK"
    L4 = "STATIC_FALLBACK"


class FallbackResult:
    def __init__(self, level, success, data=None, error_message=None):
        self.level = level
        self.success = success
        self.data = data
        self.error_message = error_message


class FallbackManager:
    def __init__(self):
        self.fallback_chain = [
            FallbackLevel.L1,
            FallbackLevel.L2,
            FallbackLevel.L3,
            FallbackLevel.L4
        ]
        self.current_level_index = 0
    
    def get_fallback_result(self, level, **kwargs):
        handlers = {
            FallbackLevel.L1: self._handle_model_fallback,
            FallbackLevel.L2: self._handle_parallel_fallback,
            FallbackLevel.L3: self._handle_cache_fallback,
            FallbackLevel.L4: self._handle_static_fallback,
        }
        
        handler = handlers.get(level, self._handle_static_fallback)
        return handler(**kwargs)
    
    def _handle_model_fallback(self, **kwargs):
        return FallbackResult(
            level=FallbackLevel.L1,
            success=True,
            data={"action": "switch_to_backup_model"}
        )
    
    def _handle_parallel_fallback(self, **kwargs):
        return FallbackResult(
            level=FallbackLevel.L2,
            success=True,
            data={"action": "execute_serially"}
        )
    
    def _handle_cache_fallback(self, **kwargs):
        return FallbackResult(
            level=FallbackLevel.L3,
            success=True,
            data={"action": "use_cached_response"}
        )
    
    def _handle_static_fallback(self, **kwargs):
        return FallbackResult(
            level=FallbackLevel.L4,
            success=True,
            data={"action": "use_static_default"}
        )
    
    def execute_with_fallback(self, primary_func, *args, **kwargs):
        try:
            result = primary_func(*args, **kwargs)
            return FallbackResult(
                level=FallbackLevel.L1,
                success=True,
                data=result
            )
        except Exception as e:
            for level in self.fallback_chain:
                fallback_result = self.get_fallback_result(level, error=e)
                if fallback_result.success:
                    return fallback_result
            
            return FallbackResult(
                level=FallbackLevel.L4,
                success=False,
                error_message="All fallbacks failed"
            )
    
    def reset(self):
        self.current_level_index = 0

