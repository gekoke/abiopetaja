from app.pdf import PDFCompilationError

type TestGenerationError = EmptyTemplate | PDFCompilationError


class EmptyTemplate:
    pass
