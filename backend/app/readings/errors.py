import asyncio


class ReadingOrchestratorError(RuntimeError):
    """Base class for explicit reading state-machine failures."""


class RuntimeTransportError(ReadingOrchestratorError):
    """The runtime command outcome is unknown at the process boundary."""


class NarrativeGenerationError(ReadingOrchestratorError):
    """The standalone model did not return a valid candidate."""

    def __init__(self, code: str, *, receipt: object | None = None) -> None:
        super().__init__(code)
        self.receipt = receipt


class NarrativeGenerationCancelled(asyncio.CancelledError):
    """External cancellation detached from sensitive model transport frames."""

    def __init__(self, *, receipt: object) -> None:
        super().__init__("model_cancelled")
        self.receipt = receipt


class OrchestratorInvariantError(ReadingOrchestratorError):
    """A dependency returned a result that violates the frozen state machine."""
