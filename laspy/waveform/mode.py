from enum import StrEnum


class WaveformMode(StrEnum):
    NEVER = "never"
    LAZY = "lazy"
    EAGER = "eager"
