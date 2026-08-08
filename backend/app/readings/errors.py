class ReadingOrchestratorError(RuntimeError):
    """Base class for explicit reading state-machine failures."""


class RuntimeTransportError(ReadingOrchestratorError):
    """The runtime command outcome is unknown at the process boundary."""


class NarrativeGenerationError(ReadingOrchestratorError):
    """The standalone model did not return a valid candidate."""


class OrchestratorInvariantError(ReadingOrchestratorError):
    """A dependency returned a result that violates the frozen state machine."""
