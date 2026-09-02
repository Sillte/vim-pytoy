from pytoy.shared.ui.pytoy_buffer import (
    BufferQuery,
    PytoyBuffer,
    PytoyBufferProvider,
)


def test_buffer_facade_uses_product_selected_backend() -> None:
    buffer = PytoyBuffer.get_current()
    buffer.init_buffer()
    source = buffer.source

    assert buffer.buffer_id
    assert buffer.source == source
    assert buffer.content == ""
    assert buffer.lines == []

    buffer.append("more")
    buffer.init_buffer("new")
    buffer.show()
    buffer.hide()

    assert buffer.content == "new"
    assert buffer.lines == ["new"]


def test_buffer_basic_content_operations() -> None:
    buffer = PytoyBuffer.get_current()
    buffer.init_buffer("first\nsecond")

    assert buffer.content == "first\nsecond"
    assert buffer.lines == ["first", "second"]

    buffer.append("third\nfourth")

    assert buffer.content == "first\nsecond\nthird\nfourth"
    assert buffer.lines == ["first", "second", "third", "fourth"]


def test_provider_wraps_and_queries_buffers() -> None:
    provider = PytoyBufferProvider()
    current = provider.get_current()
    source = current.source

    buffers = provider.get_buffers()
    queried = provider.query(BufferQuery.from_source(source))

    assert current.buffer_id in [buffer.buffer_id for buffer in buffers]
    assert [buffer.buffer_id for buffer in queried] == [current.buffer_id]
