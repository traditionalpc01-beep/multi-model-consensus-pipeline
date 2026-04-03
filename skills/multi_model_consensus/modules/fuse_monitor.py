
from __future__ import annotations


FUSE_RULES = {
    "capability_levels": {
        "L0_threshold": 0.3,
        "L1_threshold": 0.6,
        "L2_threshold": 0.8
    },
    "runtime": {
        "schema_fail_max": 3,
        "delay_max_seconds": 30,
        "error_route_max": 2,
        "token_budget_ratio": 0.8
    }
}


class FuseStatus:
    def __init__(self, any_fuse_triggered, capability_level, capability_action, 
                 delay_fuse, schema_fail_fuse, token_budget_fuse, 
                 error_route_fuse, recommended_action):
        self.any_fuse_triggered = any_fuse_triggered
        self.capability_level = capability_level
        self.capability_action = capability_action
        self.delay_fuse = delay_fuse
        self.schema_fail_fuse = schema_fail_fuse
        self.token_budget_fuse = token_budget_fuse
        self.error_route_fuse = error_route_fuse
        self.recommended_action = recommended_action


class FuseMonitor:
    def __init__(self):
        self.rules = FUSE_RULES
        self.schema_fail_count = 0
        self.error_route_count = 0
        self.elapsed_seconds = 0.0
    
    def check_capability_level(self, score):
        thresholds = self.rules["capability_levels"]
        if score &gt;= thresholds["L2_threshold"]:
            return "L2"
        elif score &gt;= thresholds["L1_threshold"]:
            return "L1"
        else:
            return "L0"
    
    def get_capability_action(self, level):
        actions = {
            "L0": "skip_consensus",
            "L1": "server_normalization",
            "L2": "normal_flow"
        }
        return actions.get(level, "normal_flow")
    
    def check_all_limits(self, used_tokens=0, total_tokens=100000):
        capability_level = self.check_capability_level(0.8)
        capability_action = self.get_capability_action(capability_level)
        
        delay_fuse = self.elapsed_seconds &gt; self.rules["runtime"]["delay_max_seconds"]
        schema_fail_fuse = self.schema_fail_count &gt;= self.rules["runtime"]["schema_fail_max"]
        token_ratio = used_tokens / total_tokens if total_tokens &gt; 0 else 0
        token_budget_fuse = token_ratio &gt;= self.rules["runtime"]["token_budget_ratio"]
        error_route_fuse = self.error_route_count &gt;= self.rules["runtime"]["error_route_max"]
        
        any_fuse_triggered = delay_fuse or schema_fail_fuse or token_budget_fuse or error_route_fuse
        
        recommended_action = capability_action
        if any_fuse_triggered:
            recommended_action = "fallback"
        
        return FuseStatus(
            any_fuse_triggered=any_fuse_triggered,
            capability_level=capability_level,
            capability_action=capability_action,
            delay_fuse=delay_fuse,
            schema_fail_fuse=schema_fail_fuse,
            token_budget_fuse=token_budget_fuse,
            error_route_fuse=error_route_fuse,
            recommended_action=recommended_action
        )
    
    def record_schema_fail(self):
        self.schema_fail_count += 1
    
    def record_error_route(self):
        self.error_route_count += 1
    
    def record_delay(self, seconds):
        self.elapsed_seconds += seconds
    
    def reset(self):
        self.schema_fail_count = 0
        self.error_route_count = 0
        self.elapsed_seconds = 0.0

