"""Reserved extension boundary; deliberately not connected to the MVP."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class FeedbackContext:
    learner_id: str
    session_id: str
    observed_weaknesses: tuple[str, ...]
    learner_reported_emotion: str | None = None
    emotion_use_consent: bool = False

class FeedbackProvider(Protocol):
    def generate(self, context: FeedbackContext) -> str:
        """Future opt-in feedback provider. Must never fabricate assessment scores."""
        ...
