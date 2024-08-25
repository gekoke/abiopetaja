type PDFCompilationError = Timeout | FailedUnexpectedly


class Timeout:
    pass


class FailedUnexpectedly:
    pass


type TestGenerationError = EmptyTemplate | PDFCompilationError


class EmptyTemplate:
    pass
