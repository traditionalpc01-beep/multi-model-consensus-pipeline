
from __future__ import annotations


ROUTING_RULES = {
    "simple": {
        "route_id": "direct_execution",
        "keywords": ["fix", "update", "change", "adjust", "modify", "add", "修复", "更新", "修改", "调整", "添加"],
    },
    "moderate": {
        "route_id": "consensus_1_round",
        "keywords": ["implement", "build", "develop", "integrate", "实现", "开发", "集成"],
    },
    "complex": {
        "route_id": "consensus_3_rounds",
        "keywords": ["architecture", "rewrite", "replace", "refactor", "migrate", "架构", "重构", "替换", "迁移", "核心"],
    },
}


class RouteChoice:
    def __init__(self, route_id, task_class, next_action):
        self.route_id = route_id
        self.task_class = task_class
        self.next_action = next_action
    
    def to_dict(self):
        return {
            "route_id": self.route_id,
            "task_class": self.task_class,
            "next_action": self.next_action
        }


class TaskRouter:
    def __init__(self):
        self.rules = ROUTING_RULES
    
    def route(self, task):
        lowered_task = task.casefold()
        
        for task_class in ("complex", "moderate", "simple"):
            rule = self.rules[task_class]
            if any(keyword.casefold() in lowered_task for keyword in rule["keywords"]):
                return RouteChoice(
                    route_id=rule["route_id"],
                    task_class=task_class,
                    next_action="execute" if task_class == "simple" else "analyze"
                )
        
        return RouteChoice(
            route_id=self.rules["moderate"]["route_id"],
            task_class="moderate",
            next_action="analyze"
        )

