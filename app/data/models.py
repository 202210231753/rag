from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

@dataclass
class UserProfile:
    user_id: str
    static_tags: List[str] = field(default_factory=list)
    location: str = ""
    negative_tags: List[str] = field(default_factory=list)
    dynamic_interests: List[str] = field(default_factory=list)

@dataclass
class Item:
    item_id: str
    content: str
    tags: List[str]
    vector: List[float] = field(default_factory=list)
    score: float = 0.0
    strategy_source: str = "algorithm"  # algorithm, hot, curated

@dataclass
class ExplanationItem:
    item: Item
    explanation: str

@dataclass
class ExperimentParams:
    diversity_lambda: float
    enable_curated: bool

@dataclass
class FeedbackAction:
    action_type: str  # view, click, dismiss
    timestamp: datetime = field(default_factory=datetime.now)

