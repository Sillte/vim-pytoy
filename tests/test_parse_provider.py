import pytest
from pytoy.infra.sub_commands.tokenizer import Token, tokenize
from pytoy.infra.sub_commands.specs import (
    ArgumentSpec,
    OptionSpec,
    SubCommandSpec,
    MainCommandSpec,
)

from pytoy.infra.sub_commands.parse_provider import ParseProvider

@pytest.fixture
def parse_provider() -> ParseProvider:
    run_spec = SubCommandSpec(
        "run",
        ArgumentSpec(
            "command",
        ),
    )
    option_specs = [
        OptionSpec("app", expects_value=True, short_option="a"),
        OptionSpec("buffer", expects_value=True, completion=["__CMD__", "__MOCK__"]),
        OptionSpec("flag", expects_value=False, short_option="f"),
    ]
    command_spec = MainCommandSpec([run_spec], options=option_specs)
    return ParseProvider(command_spec)

def test_abbreviated_case(parse_provider: ParseProvider):
    for arg_line in ["-f -a appname run command", "-fa appname run command"]:
        parsed = parse_provider(arg_line)
        assert parsed.main_options["app"] == "appname"
        assert "flag" in parsed.main_options
        assert "run" == parsed.sub_command
        assert parsed.sub_arguments[0] == "command"

def test_optional_case(parse_provider: ParseProvider):
    arg_line = "--app=appname run command"
    parsed = parse_provider(arg_line)
    assert parsed.main_options["app"] == "appname"
    assert "run" == parsed.sub_command
    assert parsed.sub_arguments[0] == "command"