import builtins
from unittest.mock import Mock

from pytoy.bootstrap.import_resolvers import LLMImportResolver
from pytoy.shared import pytoy_configuration


def test_import_error_is_logged_to_global_logger(monkeypatch):
    logger = Mock()
    configuration = Mock()
    configuration.get_logger.return_value = logger
    monkeypatch.setattr(pytoy_configuration, "PytoyConfiguration", lambda: configuration)

    original_import = builtins.__import__

    def import_with_missing_pytoy_llm(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pytoy_llm":
            raise ImportError("pytoy_llm unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_with_missing_pytoy_llm)

    resolver = LLMImportResolver()
    resolver._naive_import()

    configuration.get_logger.assert_called_once_with(location="global")
    logger.exception.assert_called_once_with("Failed to import pytoy_llm")
    assert isinstance(resolver._import_error, ImportError)
