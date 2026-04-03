from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Optional, Callable
import time


class FallbackLevel(IntEnum):
    """Enumeration of fallback levels."""
    MODEL_FALLBACK = 1
    PARALLEL_FALLBACK = 2
    CACHE_FALLBACK = 3
    STATIC_FALLBACK = 4


@dataclass
class FallbackResult:
    """Result of a fallback operation."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    level_used: Optional[FallbackLevel] = None
    latency_ms: float = 0.0


class FallbackManager:
    """
    A four-level fallback manager for handling service failures with escalating recovery strategies.
    
    The fallback strategy progresses through levels when failures occur:
    - L1: Switch to backup model on timeout/error
    - L2: Fall back from parallel to serial execution
    - L3: Use cached responses when multiple models are unavailable
    - L4: Return static default on system-level faults
    """

    def __init__(self) -> None:
        self.current_level: FallbackLevel = FallbackLevel.MODEL_FALLBACK
        self.recovery_attempts: int = 0
        self._cache: Dict[str, Any] = {}
        self._static_default: Optional[Any] = None

    def execute_with_fallback(self, 
                            primary_call: Callable[[], Any],
                            backup_call: Optional[Callable[[], Any]] = None,
                            cache_key: Optional[str] = None,
                            timeout: float = 5.0) -> FallbackResult:
        """
        Execute a function with full fallback protection across all levels.
        
        Args:
            primary_call: Primary function to execute
            backup_call: Backup function if primary fails (L1)
            cache_key: Key for cache lookup/storing (L3)
            timeout: Timeout for primary call in seconds
            
        Returns:
            FallbackResult containing outcome and metadata
        """
        start_time = time.time()
        
        # Try Level 1: Model fallback
        result = self.try_level_1(primary_call, backup_call, timeout)
        if result.success:
            return result
        
        # Try Level 2: Parallel fallback
        result = self.try_level_2(primary_call, timeout)
        if result.success:
            return result
        
        # Try Level 3: Cache fallback
        result = self.try_level_3(cache_key)
        if result.success:
            return result
        
        # Try Level 4: Static fallback
        result = self.try_level_4()
        if result.success:
            return result
        
        # All fallbacks exhausted
        latency = (time.time() - start_time) * 1000
        return FallbackResult(
            success=False,
            error="All fallback levels exhausted",
            level_used=self.current_level,
            latency_ms=latency
        )

    def try_level_1(self, 
                   primary_call: Callable[[], Any],
                   backup_call: Optional[Callable[[], Any]],
                   timeout: float) -> FallbackResult:
        """
        Level 1: Attempt primary call, fallback to backup on failure.
        
        Args:
            primary_call: Primary function to execute
            backup_call: Backup function if primary fails
            timeout: Timeout for primary call
            
        Returns:
            FallbackResult from successful execution
        """
        start_time = time.time()
        
        try:
            # Simulate timeout handling (in real implementation, use threading/async)
            result = primary_call()
            latency = (time.time() - start_time) * 1000
            return FallbackResult(success=True, data=result, level_used=FallbackLevel.MODEL_FALLBACK, latency_ms=latency)
            
        except Exception as e:
            self.escalate(FallbackLevel.PARALLEL_FALLBACK)
            
            if backup_call:
                try:
                    result = backup_call()
                    latency = (time.time() - start_time) * 1000
                    return FallbackResult(success=True, data=result, level_used=FallbackLevel.MODEL_FALLBACK, latency_ms=latency)
                except Exception as backup_error:
                    return FallbackResult(success=False, error=str(backup_error), level_used=FallbackLevel.MODEL_FALLBACK)
            else:
                return FallbackResult(success=False, error=str(e), level_used=FallbackLevel.MODEL_FALLBACK)

    def try_level_2(self, primary_call: Callable[[], Any], timeout: float) -> FallbackResult:
        """
        Level 2: Attempt parallel execution, fallback to serial on failure.
        
        Args:
            primary_call: Function to execute
            timeout: Timeout for execution
            
        Returns:
            FallbackResult from successful execution
        """
        start_time = time.time()
        
        try:
            # In real implementation, this would be actual parallel execution
            # For now, simulate parallel execution that might fail
            result = primary_call()  # Simulating parallel execution
            latency = (time.time() - start_time) * 1000
            return FallbackResult(success=True, data=result, level_used=FallbackLevel.PARALLEL_FALLBACK, latency_ms=latency)
            
        except Exception as e:
            self.escalate(FallbackLevel.CACHE_FALLBACK)
            
            # Fallback to serial execution
            try:
                result = primary_call()
                latency = (time.time() - start_time) * 1000
                return FallbackResult(success=True, data=result, level_used=FallbackLevel.PARALLEL_FALLBACK, latency_ms=latency)
            except Exception as serial_error:
                return FallbackResult(success=False, error=str(serial_error), level_used=FallbackLevel.PARALLEL_FALLBACK)

    def try_level_3(self, cache_key: Optional[str]) -> FallbackResult:
        """
        Level 3: Attempt cache retrieval, fallback to computation on cache miss.
        
        Args:
            cache_key: Key to look up in cache
            
        Returns:
            FallbackResult from cache or computed value
        """
        start_time = time.time()
        
        if not cache_key:
            self.escalate(FallbackLevel.STATIC_FALLBACK)
            return FallbackResult(success=False, error="No cache key provided", level_used=FallbackLevel.CACHE_FALLBACK)
        
        if cache_key in self._cache:
            latency = (time.time() - start_time) * 1000
            return FallbackResult(success=True, data=self._cache[cache_key], level_used=FallbackLevel.CACHE_FALLBACK, latency_ms=latency)
        
        # Cache miss - compute and store
        try:
            # In real implementation, compute the value
            computed_value = f"computed_{cache_key}"
            self._cache[cache_key] = computed_value
            
            latency = (time.time() - start_time) * 1000
            return FallbackResult(success=True, data=computed_value, level_used=FallbackLevel.CACHE_FALLBACK, latency_ms=latency)
            
        except Exception as e:
            return FallbackResult(success=False, error=str(e), level_used=FallbackLevel.CACHE_FALLBACK)

    def try_level_4(self) -> FallbackResult:
        """
        Level 4: Return static default value.
        
        Returns:
            FallbackResult with static default
        """
        start_time = time.time()
        
        if self._static_default is None:
            self._static_default = "Static default response"
        
        latency = (time.time() - start_time) * 1000
        return FallbackResult(success=True, data=self._static_default, level_used=FallbackLevel.STATIC_FALLBACK, latency_ms=latency)

    def escalate(self, new_level: FallbackLevel) -> None:
        """
        Escalate to a higher fallback level.
        
        Args:
            new_level: The new fallback level to escalate to
        """
        self.current_level = new_level
        self.recovery_attempts += 1

    def recover(self) -> None:
        """
        Recover from current state by resetting to initial fallback level.
        """
        self.current_level = FallbackLevel.MODEL_FALLBACK
        self.recovery_attempts = 0

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the fallback manager.
        
        Returns:
            Dictionary containing current state information
        """
        return {
            "current_level": self.current_level.name,
            "recovery_attempts": self.recovery_attempts,
            "cache_size": len(self._cache),
            "static_default_set": self._static_default is not None
        }