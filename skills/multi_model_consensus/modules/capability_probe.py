from __future__ import annotations

from enum import Enum


class CapabilityLevel(Enum):
    L0 = 'L0'
    L1 = 'L1'
    L2 = 'L2'


class CapabilityProbe:
    L2_THRESHOLD = 0.80
    L1_THRESHOLD = 0.50
    
    def __init__(self):
        pass
    
    def get_capability_action(self, score):
        if score &gt;= self.L2_THRESHOLD:
            level = CapabilityLevel.L2
            action = 'normal_flow'
        elif score &gt;= self.L1_THRESHOLD:
            level = CapabilityLevel.L1
            action = 'server_normalization'
        else:
            level = CapabilityLevel.L0
            action = 'skip_consensus'
        return level, action
    
    def get_execution_path(self, level):
        path_map = {
            CapabilityLevel.L0: 'skip_consensus',
            CapabilityLevel.L1: 'server_normalization',
            CapabilityLevel.L2: 'normal_flow',
        }
        return path_map.get(level, 'normal_flow')
