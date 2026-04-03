from enum import IntEnum
from typing import Dict, Tuple, Optional


class PriorityLevel(IntEnum):
    """Enumeration representing priority levels with numeric values."""
    
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


# Numeric mapping from PriorityLevel to custom numeric values
NUMERIC_MAPPING: Dict[PriorityLevel, int] = {
    PriorityLevel.CRITICAL: 10,
    PriorityLevel.HIGH: 30,
    PriorityLevel.MEDIUM: 50,
    PriorityLevel.LOW: 70,
}

# SLA configuration dictionary with availability and latency_ms
SLA_CONFIG: Dict[PriorityLevel, Dict[str, float]] = {
    PriorityLevel.CRITICAL: {"availability": 99.99, "latency_ms": 100},
    PriorityLevel.HIGH: {"availability": 99.95, "latency_ms": 500},
    PriorityLevel.MEDIUM: {"availability": 99.90, "latency_ms": 1000},
    PriorityLevel.LOW: {"availability": 99.80, "latency_ms": 5000},
}


def to_numeric(priority: PriorityLevel) -> int:
    """
    Convert a PriorityLevel to its corresponding numeric value.
    
    Args:
        priority: The priority level to convert
        
    Returns:
        The numeric value associated with the priority level
        
    Raises:
        KeyError: If the priority is not found in NUMERIC_MAPPING
    """
    return NUMERIC_MAPPING[priority]


def from_numeric(value: int) -> PriorityLevel:
    """
    Convert a numeric value back to its corresponding PriorityLevel.
    
    Args:
        value: The numeric value to convert
        
    Returns:
        The corresponding PriorityLevel
        
    Raises:
        ValueError: If no PriorityLevel maps to the given numeric value
    """
    for priority, num_val in NUMERIC_MAPPING.items():
        if num_val == value:
            return priority
    raise ValueError(f"No PriorityLevel found for numeric value {value}")


def get_sla(priority: PriorityLevel) -> Dict[str, float]:
    """
    Retrieve SLA configuration for a given priority level.
    
    Args:
        priority: The priority level to retrieve SLA for
        
    Returns:
        Dictionary containing 'availability' and 'latency_ms' keys
        
    Raises:
        KeyError: If the priority is not found in SLA_CONFIG
    """
    return SLA_CONFIG[priority]


def validate_priority(priority: PriorityLevel) -> bool:
    """
    Validate that a priority level is valid (always returns True for existing enum members).
    
    Args:
        priority: The priority level to validate
        
    Returns:
        True if the priority is valid, False otherwise
    """
    return isinstance(priority, PriorityLevel)