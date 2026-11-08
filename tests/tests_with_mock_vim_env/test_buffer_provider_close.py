from .mocks.vim import MockVim


def test_vim_provider_discards_and_closes_matching_non_file_buffers(monkeypatch, vim_env: MockVim):
    from pytoy.shared.ui.pytoy_buffer.impls.vim import PytoyBufferProviderVim

    class FakeWindow:
        def __init__(self):
            self.close_count = 0

        def close(self):
            self.close_count += 1

    class FakeBuffer:
        def __init__(self, buffer_id, is_file):
            self.buffer_id = buffer_id
            self.is_file = is_file
            self.content = None
            self.window = FakeWindow()

        def init_buffer(self, content=""):
            self.content = content

        def get_windows(self, *, only_visible):
            assert only_visible is False
            return [self.window]

    temporary = FakeBuffer(1, False)
    file_buffer = FakeBuffer(2, True)
    provider = PytoyBufferProviderVim()
    monkeypatch.setattr(provider, "_get_pytoy_buffer_vim_impls", lambda is_normal_type: [temporary, file_buffer])

    provider.close_buffers([1, 2])

    assert temporary.content == ""
    assert temporary.window.close_count == 1
    assert file_buffer.content is None
    assert file_buffer.window.close_count == 0


def test_vscode_provider_clears_matching_non_file_buffers_and_closes_editors(monkeypatch, vim_env: MockVim):
    from pytoy.shared.ui.pytoy_buffer.impls.vscode import PytoyBufferProviderVSCode
    from pytoy.shared.ui.vscode.editor import Editor
    from pytoy.shared.ui.vscode.uri import VSCodeUri

    temporary_uri = VSCodeUri(scheme="untitled", path="__terminal__")

    class FakeBuffer:
        def __init__(self, buffer_id, is_file, uri=None):
            self.buffer_id = buffer_id
            self.is_file = is_file
            self.content = None
            self.kernel = type("Kernel", (), {"vscode_uri": uri})()

        def init_buffer(self, content=""):
            self.content = content

    temporary = FakeBuffer(1, False, temporary_uri)
    file_buffer = FakeBuffer(2, True)
    provider = PytoyBufferProviderVSCode()
    monkeypatch.setattr(provider, "get_buffers", lambda is_normal_type=False: [temporary, file_buffer])
    closed = []

    def close_editors(uris):
        closed.extend(uris)

    monkeypatch.setattr(Editor, "close_editors", staticmethod(close_editors))

    provider.close_buffers([1, 2])

    assert temporary.content == ""
    assert file_buffer.content is None
    assert closed == [temporary_uri]
