from dataclasses import dataclass


class Timeout:
    pass


class FailedUnexpectedly:
    pass


@dataclass
class PDFCompilationError:
    reason: Timeout | FailedUnexpectedly


class EmptyTemplate:
    pass


@dataclass
class TestGenerationError:
    reason: EmptyTemplate | PDFCompilationError
