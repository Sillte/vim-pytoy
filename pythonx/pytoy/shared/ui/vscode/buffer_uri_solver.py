import vim

from typing import Mapping
from pytoy.shared.ui.vscode.uri import VSCodeUri


class BufferURISolver:
    @classmethod
    def _to_uri(cls, buf_name: str):
        return VSCodeUri.from_bufname(buf_name)

    @classmethod
    def _to_key(cls, uri: VSCodeUri):
        return (uri.scheme, uri.path)

    @classmethod
    def get_bufnr_to_uris(cls) -> Mapping[int, VSCodeUri]:
        return {buf.number: cls._to_uri(buf.name) for buf in vim.buffers}

    @classmethod
    def get_uri_to_bufnr(cls) -> Mapping[VSCodeUri, int]:
        return {cls._to_uri(buf.name): buf.number for buf in vim.buffers}

    @classmethod
    def get_uri_to_bufnames(cls) -> Mapping[VSCodeUri, str]:
        return {cls._to_uri(buf.name): buf.name for buf in vim.buffers}

    @classmethod
    def get_bufname_to_uris(cls) -> Mapping[str, VSCodeUri]:
        return {buf.name: cls._to_uri(buf.name) for buf in vim.buffers}

    @classmethod
    def get_bufnr(cls, uri: VSCodeUri) -> int | None:
        return cls.get_uri_to_bufnr().get(uri)

    @classmethod
    def get_bufname(cls, uri: VSCodeUri) -> str | None:
        return cls.get_uri_to_bufnames().get(uri)

    @classmethod
    def get_uri(cls, bufnr: int) -> VSCodeUri | None:
        return cls.get_bufnr_to_uris().get(bufnr)
