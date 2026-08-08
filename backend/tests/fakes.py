from app.llm.client import LLMClient


class FakeLLMClient(LLMClient):
    """Test double that returns canned responses in order, one per call."""

    def __init__(self, responses: list[str], model_name: str = "fake-model"):
        self.model_name = model_name
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete(self, *, system: str, user: str) -> str:
        self.calls.append((system, user))
        if not self._responses:
            raise AssertionError("FakeLLMClient ran out of canned responses")
        return self._responses.pop(0)
