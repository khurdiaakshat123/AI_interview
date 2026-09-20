from enum import Enum
from typing import Dict, Any, Tuple

class QualityBand(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    AVERAGE = "Average"
    WEAK = "Weak"
    INCORRECT = "Incorrect"

class FSMAction(str, Enum):
    DEEPER_FOLLOW_UP = "DEEPER_FOLLOW_UP"
    FOLLOW_UP = "FOLLOW_UP"
    LIMITED_FOLLOW_UP = "LIMITED_FOLLOW_UP"
    STOP_THREAD = "STOP_THREAD"
    PIVOT_NEXT_TOPIC = "PIVOT_NEXT_TOPIC"

class FollowUpFSM:
    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth

    def next_action(self, current_depth: int, quality_band: str) -> Tuple[FSMAction, int, bool]:
        """
        Determines the next action and next depth level.
        Returns (action, next_depth, should_switch_thread).
        """
        band = quality_band.strip().capitalize()

        # If already reached maximum depth, we must conclude the current thread
        if current_depth >= self.max_depth:
            return FSMAction.PIVOT_NEXT_TOPIC, current_depth, True

        if band == QualityBand.EXCELLENT:
            # Go deeper aggressively
            return FSMAction.DEEPER_FOLLOW_UP, current_depth + 1, False

        elif band == QualityBand.GOOD:
            # Normal progression
            return FSMAction.FOLLOW_UP, current_depth + 1, False

        elif band == QualityBand.AVERAGE:
            # Allow limited exploration up to depth 3, then pivot
            if current_depth < 3:
                return FSMAction.LIMITED_FOLLOW_UP, current_depth + 1, False
            else:
                return FSMAction.PIVOT_NEXT_TOPIC, current_depth, True

        elif band == QualityBand.WEAK:
            # If shallow (depth 1), give one simpler follow-up or pivot
            if current_depth == 1:
                return FSMAction.LIMITED_FOLLOW_UP, current_depth + 1, False
            else:
                return FSMAction.PIVOT_NEXT_TOPIC, current_depth, True

        else:  # Incorrect
            # Stop immediately and pivot to another topic/project
            return FSMAction.PIVOT_NEXT_TOPIC, current_depth, True
