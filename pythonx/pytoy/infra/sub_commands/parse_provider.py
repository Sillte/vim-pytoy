try:
    from pytoy.infra.sub_commands.tokenizer import Token, tokenize
    from pytoy.infra.sub_commands.specs import (
        ArgumentSpec,
        OptionSpec,
        OptionType,
        Completion,
        SubCommandSpec,
        MainCommandSpec,
        CompletionContext,
        ContextType,
        ParsedArguments
    )
    from pytoy.infra.sub_commands.completion_context_maker import CompletionContextMaker
except ImportError:
    from tokenizer import Token, tokenize
    from specs import (
        ArgumentSpec,
        OptionSpec,
        OptionType,
        Completion,
        SubCommandSpec,
        MainCommandSpec,
        CompletionContext,
        ContextType,
        ParsedArguments
    )
    from completion_context_maker import CompletionContextMaker

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ParsedCommand:
    """Result of parsed `arg: str`."""

    sub_command: str | None
    main_options: dict[str, str]
    main_arguments: list[str]
    sub_options: dict[str, str]
    sub_arguments: list[str]




class _OptionParser:
    def __init__(self, spec: MainCommandSpec | SubCommandSpec, arg_line: str):
        self.spec = spec
        self.expect_value_options: dict[str, OptionSpec] = {
            option.name: option for option in spec.options if option.expects_value
        }

        self.non_value_options = {
            option.name: option for option in spec.options if not option.expects_value
                }

        self.char_to_option: dict[str, str]  = {option.short_option: option.name for option in spec.options
                                                 if option.short_option}

        self.arg_line = arg_line

    def parse(
        self,
        idx: int,
        tokens: list[Token],
        options: dict[str, OptionType | None],
        arguments: list[str],
    ) -> int:
        """Update `options` and `short_options` and return the next `idx`.

        `options` and `short_options` and `arguments` are updated.

        """
        token = tokens[idx]
        next_token = tokens[idx + 1] if idx + 1 < len(tokens) else None
        additional_idx = 1

        if token.value == "--":
            arg = self.arg_line[token.end :]
            arguments.append(arg)
            return len(tokens)  # End of loop.
        elif token.value.startswith("--"):
            if "=" in token.value:
                key, value = token.value.strip("--").split("=", 1)
                options[key] = value
            else:
                key = token.value.strip("--")
                if key in self.expect_value_options:
                    if next_token:
                        options[key] = next_token.value
                        additional_idx = 2  # Consumed one more token
                    else:
                        options[key] = self.expect_value_options[key].default
                elif key in self.non_value_options:
                    options[key] = self.non_value_options[key].default
                else:
                    options[key] = None
        elif token.value.startswith("-") and len(token.value) > 1:  # "-cf"
            for char in token.value[1:-1]:  # handling of `c` inside `cf`
                if char not in self.char_to_option:
                    raise ValueError(f"{char=} is not related to options.")
                option_name = self.char_to_option[char]
                if option_name in self.expect_value_options:
                    raise ValueError(f"{option_name=}, {char=} cannot be allowed here.")
                options[option_name] = self.non_value_options[option_name].default
            last_char = token.value[-1]
            if last_char not in self.char_to_option:
                raise ValueError(f"{last_char=} is not related to options.")
            option_name = self.char_to_option[last_char]
            if option_name in self.expect_value_options: # -f filename.
                if next_token:
                    options[option_name] = next_token.value
                    additional_idx = 2  # Consumed one more token
                else:
                    options[option_name] = self.expect_value_options[option_name].default
            elif option_name in self.non_value_options:
                options[option_name] = self.non_value_options[option_name].default
            else:
                assert False, "Implementation Error"
        else:
            arguments.append(token.value)
        return idx + additional_idx


def make_parsed_command(main_spec: MainCommandSpec, arg_line: str) -> ParsedCommand:
    
    tokens = tokenize(arg_line)
    #print("tokens", tokens, arg_line)
    # `token` starts from `0`, this is differnt from `cmd_line`.
    idx = 0

    sub_names = {command.name: command for command in main_spec.commands}
    sub_spec: None | SubCommandSpec = None
    main_options = dict()
    main_arguments = []

    main_parser = _OptionParser(main_spec, arg_line)

    while idx < len(tokens):
        token = tokens[idx]
        #print("token", token, idx)

        if token.value in sub_names:
            sub_spec = sub_names[token.value]
            idx = idx + 1
            break
        idx = main_parser.parse(
            idx, tokens, main_options, main_arguments
        )

    if not sub_spec:
        return ParsedCommand(
            sub_command=None,
            main_options=main_options,
            main_arguments=main_arguments,
            sub_options={},
            sub_arguments=[],
        )

    sub_options = dict()
    sub_arguments = []

    sub_parser = _OptionParser(sub_spec, arg_line)

    while idx < len(tokens):
        token = tokens[idx]
        idx = sub_parser.parse(
            idx, tokens, sub_options, sub_arguments
        )

    return ParsedCommand(
        sub_command=sub_spec.name,
        main_options=main_options,
        main_arguments=main_arguments,
        sub_options=sub_options,
        sub_arguments=sub_arguments,
    )


def to_parsed_arguments(
    main_spec: MainCommandSpec, parsed_command: ParsedCommand
) -> ParsedArguments:
    """
    [NOTE]:
    1. Currently, non-existent check is not performed in this layer. 
    2. Currently, inconsistency of definition is not yet checked.
    """,
    #print("ParsedCommand", parsed_command)


    def _type_conversion(
        spec: MainCommandSpec | SubCommandSpec, options: dict[str, str | None]
    ) -> dict[str, OptionType | None]:
        result = dict()
        name_to_spec = {spec.name: spec for spec in spec.options}

        for key, value in options.items():
            if key in name_to_spec:
                opt_spec = name_to_spec[key]
                if opt_spec.type and value is not None:
                    value = opt_spec.type(value)
                else:
                    value = value
            result[key] = value
        return result

    main_options = parsed_command.main_options
    sub_options = parsed_command.sub_options

    main_options = _type_conversion(main_spec, main_options)
    if parsed_command.sub_command:
        name_to_spec = {spec.name: spec for spec in main_spec.commands}
        sub_spec = name_to_spec[parsed_command.sub_command]
        sub_options = _type_conversion(sub_spec, sub_options)
    return ParsedArguments(
        sub_command=parsed_command.sub_command,
        main_options=main_options,
        main_arguments=parsed_command.main_arguments,
        sub_options=sub_options,
        sub_arguments=parsed_command.sub_arguments,
    )


class ParseProvider:
    def __init__(self, main_spec: MainCommandSpec):
        self._main_spec = main_spec

    @property
    def main_spec(self) -> MainCommandSpec:
        return self._main_spec

    def __call__(self, arg_line: str) -> ParsedArguments:
        parsed_command = make_parsed_command(self.main_spec, arg_line)
        return to_parsed_arguments(self.main_spec, parsed_command)


if __name__ == "__main__":
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
    provider = ParseProvider(command_spec)

    def test_1():
        for arg_line in ["-f -a appname run command", "-fa appname run command"]:
            arg_line = "-f -a appname run command"
            parsed = provider(arg_line)
            assert parsed.main_options["app"] == "appname"
            assert "flag" in parsed.main_options
            assert "run" == parsed.sub_command
            assert parsed.sub_arguments[0] == "command"
    test_1()

    def test_2():
        arg_line = "--app=appname run command"
        parsed = provider(arg_line)
        assert parsed.main_options["app"] == "appname"
        assert "run" == parsed.sub_command
        assert parsed.sub_arguments[0] == "command"
    test_2()


