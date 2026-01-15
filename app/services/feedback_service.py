from typing import Dict, List
from app.data.models import FeedbackAction

class FeedbackService:
    def __init__(self):
        # 内存中存储反馈
        self._feedback_store: Dict[str, List[FeedbackAction]] = {} # 追踪ID -> 动作
        self._strategy_stats: Dict[str, Dict[str, int]] = {} # 版本 -> {点击数: 0, 浏览数: 0}

    def submit_feedback(self, trace_id: str, item_id: str, action_type: str) -> None:
        """
        接收前端埋点（曝光/点击/关闭）。
        """
        if trace_id not in self._feedback_store:
            self._feedback_store[trace_id] = []
        
        self._feedback_store[trace_id].append(FeedbackAction(action_type=action_type))
        print(f"[FeedbackService] Recorded {action_type} for trace {trace_id} on item {item_id}")

    def get_strategy_report(self, strategy_version: str) -> Dict[str, int]:
        """
        统计不同策略的点击率。
        """
        # 模拟返回统计数据的逻辑
        return self._strategy_stats.get(strategy_version, {"views": 100, "clicks": 5})
