"""
Tests for Phase 2.6 modules: weighted_consensus, priority_level, fallback_manager
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from weighted_consensus import WeightedScoreConsensus, ModelResponse, ConsensusResult
from priority_level import PriorityLevel, to_numeric, from_numeric, get_sla, validate_priority, NUMERIC_MAPPING, SLA_CONFIG
from fallback_manager import FallbackManager, FallbackLevel, FallbackResult


class TestWeightedScoreConsensus:
    """Tests for WeightedScoreConsensus class."""
    
    def test_weights_are_correct(self):
        """Verify weights match consensus: 40/30/20/10"""
        consensus = WeightedScoreConsensus()
        assert consensus.WEIGHTS['quality'] == 0.40
        assert consensus.WEIGHTS['cost'] == 0.30
        assert consensus.WEIGHTS['latency'] == 0.20
        assert consensus.WEIGHTS['confidence'] == 0.10
    
    def test_thresholds_are_correct(self):
        """Verify thresholds match consensus: 0.75/0.50"""
        consensus = WeightedScoreConsensus()
        assert consensus.FULL_THRESHOLD == 0.75
        assert consensus.PARTIAL_THRESHOLD == 0.50
    
    def test_calculate_weighted_score(self):
        """Test weighted score calculation."""
        consensus = WeightedScoreConsensus()
        response = ModelResponse(
            quality=0.8,
            cost=0.9,  # high cost = lower cost_score
            latency=0.7,
            confidence=0.85
        )
        score = consensus.calculate_weighted_score(response)
        # 0.8*0.4 + 0.9*0.3 + 0.7*0.2 + 0.85*0.1 = 0.32 + 0.27 + 0.14 + 0.085 = 0.815
        assert 0.8 <= score <= 0.82
    
    def test_full_consensus(self):
        """Test full consensus when score >= 0.75"""
        consensus = WeightedScoreConsensus()
        responses = [
            ModelResponse(quality=0.9, cost=0.9, latency=0.9, confidence=0.9),
            ModelResponse(quality=0.85, cost=0.85, latency=0.85, confidence=0.85)
        ]
        result = consensus.evaluate(responses)
        assert result.consensus_level == "full"
        assert result.weighted_score >= 0.75
    
    def test_partial_consensus(self):
        """Test partial consensus when score >= 0.50"""
        consensus = WeightedScoreConsensus()
        responses = [
            ModelResponse(quality=0.6, cost=0.6, latency=0.6, confidence=0.6)
        ]
        result = consensus.evaluate(responses)
        assert result.consensus_level == "partial"
        assert result.weighted_score >= 0.50
    
    def test_none_consensus(self):
        """Test no consensus when score < 0.50"""
        consensus = WeightedScoreConsensus()
        responses = [
            ModelResponse(quality=0.3, cost=0.3, latency=0.3, confidence=0.3)
        ]
        result = consensus.evaluate(responses)
        assert result.consensus_level == "none"
        assert result.weighted_score < 0.50
    
    def test_empty_responses_raises_error(self):
        """Test that empty responses raises ValueError."""
        consensus = WeightedScoreConsensus()
        with pytest.raises(ValueError):
            consensus.evaluate([])


class TestPriorityLevel:
    """Tests for PriorityLevel enum."""
    
    def test_enum_values(self):
        """Verify enum values match consensus: CRITICAL=0, HIGH=1, MEDIUM=2, LOW=3"""
        assert PriorityLevel.CRITICAL.value == 0
        assert PriorityLevel.HIGH.value == 1
        assert PriorityLevel.MEDIUM.value == 2
        assert PriorityLevel.LOW.value == 3
    
    def test_numeric_mapping(self):
        """Verify numeric mapping: 10/30/50/70"""
        assert NUMERIC_MAPPING[PriorityLevel.CRITICAL] == 10
        assert NUMERIC_MAPPING[PriorityLevel.HIGH] == 30
        assert NUMERIC_MAPPING[PriorityLevel.MEDIUM] == 50
        assert NUMERIC_MAPPING[PriorityLevel.LOW] == 70
    
    def test_to_numeric(self):
        """Test to_numeric function."""
        assert to_numeric(PriorityLevel.CRITICAL) == 10
        assert to_numeric(PriorityLevel.HIGH) == 30
        assert to_numeric(PriorityLevel.MEDIUM) == 50
        assert to_numeric(PriorityLevel.LOW) == 70
    
    def test_from_numeric(self):
        """Test from_numeric function."""
        assert from_numeric(10) == PriorityLevel.CRITICAL
        assert from_numeric(30) == PriorityLevel.HIGH
        assert from_numeric(50) == PriorityLevel.MEDIUM
        assert from_numeric(70) == PriorityLevel.LOW
    
    def test_from_numeric_invalid_raises(self):
        """Test that invalid numeric raises ValueError."""
        with pytest.raises(ValueError):
            from_numeric(999)
    
    def test_get_sla(self):
        """Test get_sla function returns dict with availability and latency_ms."""
        sla = get_sla(PriorityLevel.CRITICAL)
        assert 'availability' in sla
        assert 'latency_ms' in sla
        assert sla['availability'] == 99.99
    
    def test_validate_priority(self):
        """Test validate_priority function."""
        assert validate_priority(PriorityLevel.HIGH) is True
        assert validate_priority(PriorityLevel.CRITICAL) is True


class TestFallbackManager:
    """Tests for FallbackManager class."""
    
    def test_fallback_level_enum(self):
        """Verify FallbackLevel enum: MODEL=1, PARALLEL=2, CACHE=3, STATIC=4"""
        assert FallbackLevel.MODEL_FALLBACK.value == 1
        assert FallbackLevel.PARALLEL_FALLBACK.value == 2
        assert FallbackLevel.CACHE_FALLBACK.value == 3
        assert FallbackLevel.STATIC_FALLBACK.value == 4
    
    def test_initial_level_is_model_fallback(self):
        """Test initial level is MODEL_FALLBACK."""
        manager = FallbackManager()
        assert manager.current_level == FallbackLevel.MODEL_FALLBACK
    
    def test_successful_primary_call(self):
        """Test successful primary call returns success."""
        manager = FallbackManager()
        
        def primary():
            return "success"
        
        result = manager.execute_with_fallback(primary_call=primary)
        assert result.success is True
        assert result.data == "success"
    
    def test_fallback_to_backup(self):
        """Test fallback to backup when primary fails."""
        manager = FallbackManager()
        
        def primary():
            raise Exception("primary failed")
        
        def backup():
            return "backup success"
        
        result = manager.execute_with_fallback(
            primary_call=primary,
            backup_call=backup
        )
        assert result.success is True
        assert result.data == "backup success"
    
    def test_escalate(self):
        """Test escalate increases level."""
        manager = FallbackManager()
        assert manager.current_level == FallbackLevel.MODEL_FALLBACK
        manager.escalate(FallbackLevel.PARALLEL_FALLBACK)
        assert manager.current_level == FallbackLevel.PARALLEL_FALLBACK
        assert manager.recovery_attempts == 1
    
    def test_recover(self):
        """Test recover resets to initial level."""
        manager = FallbackManager()
        manager.current_level = FallbackLevel.CACHE_FALLBACK
        manager.recovery_attempts = 5
        manager.recover()
        assert manager.current_level == FallbackLevel.MODEL_FALLBACK
        assert manager.recovery_attempts == 0
    
    def test_get_status(self):
        """Test get_status returns current state."""
        manager = FallbackManager()
        status = manager.get_status()
        assert 'current_level' in status
        assert 'recovery_attempts' in status


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])