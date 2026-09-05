import pytest

from pytoy.shared.lib.function import FunctionRegistry, RegisteredFunction


def test_function_registry_public_api_registers_and_deregisters_function():
    def function(value: str) -> str:
        return value.upper()

    registered = FunctionRegistry.register(function, name="public_function")

    assert isinstance(registered, RegisteredFunction)
    assert registered.name == "public_function"
    assert registered("value") == "VALUE"
    assert FunctionRegistry.is_registered("public_function")

    FunctionRegistry.deregister(registered)

    assert not FunctionRegistry.is_registered("public_function")


def test_function_registry_public_api_rejects_duplicate_names():
    FunctionRegistry.register(lambda: None, name="duplicate")

    with pytest.raises(ValueError):
        FunctionRegistry.register(lambda: None, name="duplicate")


def test_function_registry_public_api_generates_prefixed_name():
    def function():
        return None

    registered = FunctionRegistry.register(function, prefix="test")

    assert registered.name.startswith("test_function_")
