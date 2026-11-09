"""Unit tests for PytoyBufferVim implementation."""

# Now we can import our actual implementation

from .mocks.vim import MockVim


def test_buffer_init(vim_env: MockVim):
    """Test buffer initialization and content setting"""
    from pytoy.shared.ui.pytoy_buffer.impls.vim import PytoyBufferVim, VimBufferKernel

    # Setup
    buf = vim_env.create_buffer(1, "test.txt")
    kernel_registry = dict()
    kernel_registry[1] = VimBufferKernel(1)
    assert kernel_registry.get(1)

    class DummyCtx:
        @property
        def buffer_kernel_registry(self):
            return kernel_registry

    pytoy_buf = PytoyBufferVim(buf.number, ctx=DummyCtx())  # type: ignore
    assert pytoy_buf._kernel is not None

    # Test empty init
    pytoy_buf.init_buffer()
    assert buf._content == [""]
    assert pytoy_buf.content == ""
    assert pytoy_buf.lines == [""]

    # Test with content
    test_content = "line1\r\nline2\n\n\nline3"
    pytoy_buf.init_buffer(test_content)
    assert buf._content == ["line1", "line2", "", "", "line3"]

    pytoy_buf.init_buffer("line1\r\n")
    assert pytoy_buf.lines == ["line1", ""]

    pytoy_buf.init_buffer("line1")
    pytoy_buf.append("line2")
    assert pytoy_buf.lines == ["line1", "line2"]

    pytoy_buf.init_buffer("line1\n")
    pytoy_buf.append("line2")
    assert pytoy_buf.lines == ["line1", "line2"]


def test_buffer_append_reads_only_the_last_line(vim_env: MockVim, monkeypatch):
    import pytest

    from pytoy.shared.ui.pytoy_buffer.impls.vim import PytoyBufferVim, VimBufferKernel

    buf = vim_env.create_buffer(1, "test.txt", content=["first", "last"])
    kernel_registry = {1: VimBufferKernel(1)}

    class DummyCtx:
        @property
        def buffer_kernel_registry(self):
            return kernel_registry

    pytoy_buf = PytoyBufferVim(buf.number, ctx=DummyCtx())  # type: ignore

    def fail_full_content_read(_: VimBufferKernel) -> str:
        pytest.fail("append() must not read the full buffer content")

    monkeypatch.setattr(VimBufferKernel, "content", property(fail_full_content_read))

    original_getitem = type(buf).__getitem__
    accessed_indices = []

    def track_getitem(buffer, index):
        if isinstance(index, slice):
            pytest.fail("append() must not read all buffer lines")
        accessed_indices.append(index)
        return original_getitem(buffer, index)

    monkeypatch.setattr(type(buf), "__getitem__", track_getitem)

    pytoy_buf.append("next")

    assert accessed_indices == [-1]
    assert buf._content == ["first", "last", "next"]


def test_vscode_buffer_append_delegates_separator_to_document(monkeypatch):
    import pytest

    from pytoy.shared.ui.pytoy_buffer.impls.vscode import PytoyBufferVSCode

    class DocumentStub:
        def __init__(self) -> None:
            self.appended: list[tuple[str, bool]] = []

        @property
        def content(self) -> str:
            pytest.fail("append() must not read the full document content")

        def append(self, text: str, *, ensure_line_boundary: bool = False) -> bool:
            self.appended.append((text, ensure_line_boundary))
            return True

    document = DocumentStub()
    monkeypatch.setattr(PytoyBufferVSCode, "document", property(lambda _: document))
    buffer = object.__new__(PytoyBufferVSCode)

    buffer.append("first\r\nsecond")

    assert document.appended == [("first\nsecond", True)]


def test_document_append_uses_only_last_line_for_separator(monkeypatch):
    from pytoy.shared.ui.vscode import document as document_module
    from pytoy.shared.ui.vscode.document import Document
    from pytoy.shared.ui.vscode.uri import VSCodeUri

    calls = []

    class FakeApi:
        def eval_with_return(self, js_code, *, with_await, opts):
            calls.append((js_code, with_await, opts))
            return True

    monkeypatch.setattr(document_module, "Api", FakeApi)
    document = Document(uri=VSCodeUri(scheme="file", path="/tmp/test.txt"))

    assert document.append("next", ensure_line_boundary=True)

    js_code, with_await, opts = calls[0]
    assert with_await
    assert opts["args"]["ensureLineBoundary"] is True
    assert "doc.lineAt(lastLine).text" in js_code
    assert "lastLineText.length > 0" in js_code
    assert "doc.getText()" not in js_code


def test_vscode_replace_text_compares_normalized_content(monkeypatch):
    from pytoy.shared.lib.text import CharacterRange, CursorPosition
    from pytoy.shared.ui.pytoy_buffer.impls.vscode import range_operator as range_operator_module

    replaced_range = CharacterRange(CursorPosition(0, 0), CursorPosition(1, 1))
    sync_results = []
    replaced_texts = []

    class RangeHandlerStub:
        def __init__(self, bufnr):
            pass

        def replace_text(self, character_range, text):
            replaced_texts.append(text)
            return replaced_range

    class DocumentStub:
        def get_range(self, start_line, start_col, end_line, end_col):
            return "first\nsecond"

    def wait_until_true(predicate, *, timeout):
        result = predicate()
        sync_results.append(result)
        return result

    monkeypatch.setattr(range_operator_module, "VimBufferRangeHandler", RangeHandlerStub)
    monkeypatch.setattr(range_operator_module, "wait_until_true", wait_until_true)
    monkeypatch.setattr(range_operator_module.RangeOperatorVSCode, "bufnr", property(lambda _: 1))
    monkeypatch.setattr(range_operator_module.RangeOperatorVSCode, "document", property(lambda _: DocumentStub()))
    operator = object.__new__(range_operator_module.RangeOperatorVSCode)

    result = operator.replace_text(replaced_range, "first\r\nsecond")

    assert result == replaced_range
    assert replaced_texts == ["first\nsecond"]
    assert sync_results == [True]


def test_vscode_replace_text_logs_mismatch_without_content(monkeypatch):
    from unittest.mock import Mock

    from pytoy.shared.lib.text import CharacterRange, CursorPosition
    from pytoy.shared.ui.pytoy_buffer.impls.vscode import range_operator as range_operator_module

    replaced_range = CharacterRange(CursorPosition(0, 0), CursorPosition(1, 1))
    logger = Mock()

    class RangeHandlerStub:
        def __init__(self, bufnr):
            pass

        def replace_text(self, character_range, text):
            return replaced_range

    class DocumentStub:
        def get_range(self, start_line, start_col, end_line, end_col):
            return "different"

    class ConfigurationStub:
        def get_logger(self, *, location, level):
            assert location == "global"
            assert level == range_operator_module.logging.INFO
            return logger

    monkeypatch.setattr(range_operator_module, "VimBufferRangeHandler", RangeHandlerStub)
    monkeypatch.setattr(range_operator_module, "wait_until_true", lambda predicate, *, timeout: False)
    monkeypatch.setattr(range_operator_module, "PytoyConfiguration", ConfigurationStub)
    monkeypatch.setattr(range_operator_module.RangeOperatorVSCode, "bufnr", property(lambda _: 1))
    monkeypatch.setattr(range_operator_module.RangeOperatorVSCode, "document", property(lambda _: DocumentStub()))
    operator = object.__new__(range_operator_module.RangeOperatorVSCode)
    operator._logger = None

    operator.replace_text(replaced_range, "sensitive\r\ncontent")

    logger.error.assert_called_once()
    log_message, _, expected_length, actual_length = logger.error.call_args.args
    assert "expected_length=%d" in log_message
    assert expected_length == 17
    assert actual_length == 9
    assert "sensitive\r\ncontent" not in logger.error.call_args.args


def test_buffer_valid(vim_env: MockVim):
    """Test valid property"""
    # Setup kernel registry
    from pytoy.shared.ui.pytoy_buffer.impls.vim import PytoyBufferVim, VimBufferKernel

    kernel_registry = dict()

    # Create buffer first
    buf = vim_env.create_buffer(1, "test.txt")
    buf.valid = True

    # Create kernel that will retrieve the buffer from vim_env
    kernel = VimBufferKernel(1)
    kernel_registry[1] = kernel

    class DummyCtx:
        @property
        def buffer_kernel_registry(self):
            return kernel_registry

    pytoy_buf = PytoyBufferVim(buf.number, ctx=DummyCtx())  # type: ignore
    assert pytoy_buf.valid

    # Test invalid buffer by making it invalid
    buf.valid = False
    assert not pytoy_buf.valid
