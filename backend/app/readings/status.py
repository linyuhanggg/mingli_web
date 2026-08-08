from enum import StrEnum


class ReadingStatus(StrEnum):
    INPUT_READY = "input_ready"
    WAITING_INPUT = "waiting_input"
    TERMINAL_STOPPED = "terminal_stopped"
    PREPARED = "prepared"
    COMPLETING = "completing"
    ACCEPTED = "accepted"
    DELAYED = "delayed"
    RUNTIME_UNKNOWN = "runtime_unknown"
