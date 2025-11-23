import vim

from typing import Mapping
from pytoy.ui.vscode.uri import Uri


class BufferURISolver:
    @classmethod
    def _to_uri(cls, buf_name: str):
        return Uri.from_bufname(buf_name)

    @classmethod
    def _to_key(cls, uri: Uri):
        return (uri.scheme, uri.path)

    @classmethod
    def get_bufnr_to_uris(cls) -> Mapping[int, Uri]:
        return {buf.number: cls._to_uri(buf.name) for buf in vim.buffers}

    @classmethod
    def get_uri_to_bufnr(cls) -> Mapping[Uri, int]:
        return {cls._to_uri(buf.name): buf.number for buf in vim.buffers}

    @classmethod
    def get_uri_to_bufnames(cls) -> Mapping[Uri, str]:
        return {cls._to_uri(buf.name): buf.name for buf in vim.buffers}

    @classmethod
    def get_bufname_to_uris(cls) -> Mapping[str, Uri]:
        return {buf.name: cls._to_uri(buf.name) for buf in vim.buffers}

    @classmethod
    def get_bufnr(cls, uri: Uri) -> int | None:
        return cls.get_uri_to_bufnr().get(uri)

    @classmethod
    def get_uri(cls, bufnr: int) -> Uri | None:
        return cls.get_bufnr_to_uris().get(bufnr)
