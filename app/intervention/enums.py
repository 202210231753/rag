from __future__ import annotations

from enum import Enum


class WhitelistStatus(str, Enum):
    locked = "locked"
    unlocked = "unlocked"


class MiningStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class CensorSource(str, Enum):
    manual = "manual"
    mined = "mined"


class CensorPolicyAction(str, Enum):
    allow = "allow"  # do nothing
    mask = "mask"  # mask matched words
    refuse = "refuse"  # refuse processing
    lock_user = "lock_user"  # lock user (requires whitelist/lock integration upstream)
