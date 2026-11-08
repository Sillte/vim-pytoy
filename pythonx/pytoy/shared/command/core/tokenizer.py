import shlex
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Mapping, Self, Sequence, get_args

from pytoy.shared.command.core.models import MISSING_DEFAULT, BooleanOptions, CommandModel, Token, _is_sequence_type


class OptionValueMissingError(Exception):
    def __init__(self, option_key: str):
        self.option_key = option_key
        message = f"Option '{option_key}' requires a value, but none was provided."
        super().__init__(message)

    def __str__(self) -> str:
        return f"Missing value for option: {self.option_key}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(option_key={self.option_key!r})"


class BooleanOptionTakesNoValue(Exception):
    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Boolean option '{key}' does not take a value")


@dataclass(frozen=True)
class InterpretedInput:
    arguments: Sequence[str]
    options: Mapping[str, list[str | bool]]
    exceptions: Sequence[Exception] = field(default_factory=list)

    @classmethod
    def from_tokens(cls, tokens: Sequence[Token], boolean_options: CommandModel | BooleanOptions) -> Self:
        if isinstance(boolean_options, CommandModel):
            boolean_options = BooleanOptions.from_command_model(boolean_options)

        arguments = []
        options = defaultdict(list)
        exceptions = []

        tokens = list(tokens)  # イテレータではなくリストでインデックス管理
        i = 0
        while i < len(tokens):
            token = tokens[i]
            val = token.value

            if val.startswith("--"):
                key_val = val[2:]
                is_no_flag = False
                if key_val.startswith("no-"):
                    key_val = key_val[3:]
                    is_no_flag = True

                if "=" in key_val:
                    key, str_val = key_val.split("=", 1)
                else:
                    key = key_val
                    str_val = True
                    if i + 1 < len(tokens):
                        next_token_val = tokens[i + 1].value
                        if not next_token_val.startswith("--"):
                            str_val = next_token_val
                            i += 1  # 値として消費
                    elif key not in boolean_options.names:
                        exceptions.append(OptionValueMissingError(key))

                if key in boolean_options.names:
                    if not isinstance(str_val, bool):
                        exceptions.append(BooleanOptionTakesNoValue(key))
                    str_val = not is_no_flag

                options[cls.convert_key(key)].append(str_val)
            else:
                arguments.append(token.value)
            i += 1
        return cls(arguments=arguments, options=options, exceptions=exceptions)

    @classmethod
    def convert_key(cls, key: str) -> str:
        """`-` in option is normalize to `_`."""
        return key.replace("-", "_")

    @classmethod
    def revert_key(cls, key: str) -> str:
        """`-` in option is normalize to `_`."""
        return key.replace("_", "-")


@dataclass(frozen=True)
class ResolvedInput:
    arg_kwargs: Mapping[str, Any]
    kwargs: Mapping[str, Any]

    @classmethod
    def _convert_element(
        cls,
        val: Any,
        element_types: Sequence[type] | set[type],
        literal_values: Sequence[Any] | None,
        only_literal: bool = False,
    ):
        if literal_values is not None:
            for elem in literal_values:
                try:
                    if type(elem)(val) == elem:
                        return type(elem)(val)
                except Exception:
                    pass
            if only_literal:
                raise ValueError(f"Given `value` ({val}) does not satisfy the literal condition.")

        converted = MISSING_DEFAULT

        for typ in sorted(element_types, key=lambda t: t is str):
            try:
                # bool 型でフラグが渡されている場合、そのまま利用
                if typ is bool and isinstance(val, bool):
                    converted = val
                    break
                converted = typ(val)
                break
            except Exception:
                continue
        return converted

    @classmethod
    def from_interpreted_input(cls, command_model: CommandModel, interpreted_input: InterpretedInput) -> Self:
        if interpreted_input.exceptions:
            raise interpreted_input.exceptions[0]

        kwargs = {}

        arg_kwargs = {}

        if len(interpreted_input.arguments) > len(command_model.arguments):
            raise ValueError("Too many arguments")
        positional_argument_order = command_model.positional_argument_order
        required_count = sum(argument.required for argument in positional_argument_order)

        if len(interpreted_input.arguments) < required_count:
            raise ValueError("Too little arguments")
        given_arguments = positional_argument_order[: len(interpreted_input.arguments)]
        non_given_arguments = positional_argument_order[len(interpreted_input.arguments) :]
        for i, arg_def in enumerate(given_arguments):
            val_str = interpreted_input.arguments[i]
            converted = cls._convert_element(val_str, arg_def.types, arg_def.literal_values, arg_def.only_literal)
            if converted is MISSING_DEFAULT:
                raise TypeError(f"Cannot convert argument '{arg_def.name}' value '{val_str}' to any allowed type")
            arg_kwargs[arg_def.name] = converted

        for arg_def in non_given_arguments:
            value = arg_def.default
            if value is MISSING_DEFAULT:
                raise TypeError(f"Cannot convert argument '{arg_def.name}' does not have the default.")
            arg_kwargs[arg_def.name] = value

        for opt_def in command_model.options:
            name = opt_def.name
            values = interpreted_input.options.get(name, [])

            if not values:
                default_value = opt_def.default
                kwargs[name] = default_value
                continue

            converted_values = MISSING_DEFAULT

            for typ in opt_def.types:
                if _is_sequence_type(typ):
                    elem_types = get_args(typ)
                    converted_values = [cls._convert_element(val, elem_types, None) for val in values]
                    if any(elem is MISSING_DEFAULT for elem in converted_values):
                        continue
                    else:
                        break
                else:
                    try:
                        if typ is bool:
                            if not isinstance(values[-1], bool):
                                raise ValueError(f"Boolean option '{name}' does not accept value")
                            converted_values = values[-1]
                        else:
                            converted_values = typ(values[-1])
                        break
                    except Exception:
                        pass
            if converted_values is MISSING_DEFAULT:
                raise ValueError(f"Given `{values}` are not appropriate for `{name}`")
            kwargs[name] = converted_values

        for key in interpreted_input.options:
            if key not in {opt.name for opt in command_model.options}:
                raise ValueError(f"Unknown option: {key}")

        return cls(arg_kwargs=arg_kwargs, kwargs=kwargs)


def _iter_raw_token_ranges(cmd_line: str):
    index = 0
    while index < len(cmd_line):
        while index < len(cmd_line) and cmd_line[index] in " \t\r\n":
            index += 1
        if index == len(cmd_line):
            return

        start = index
        quote = None
        escaped = False
        while index < len(cmd_line):
            char = cmd_line[index]
            if escaped:
                escaped = False
            elif char == "\\" and quote != "'":
                escaped = True
            elif quote is not None:
                if char == quote:
                    quote = None
            elif char in "'\"":
                quote = char
            elif char in " \t\r\n":
                break
            index += 1

        yield start, index


def _is_single_quoted_token(raw_token: str) -> bool:
    if len(raw_token) < 2 or raw_token[0] not in "'\"":
        return False

    quote = raw_token[0]
    escaped = False
    for index, char in enumerate(raw_token[1:], start=1):
        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif char == quote:
            return index == len(raw_token) - 1
    return False


def tokenize(cmd_line: str) -> list[Token]:
    """Tokenize input while retaining source positions for each token."""
    tokens = []
    for start, end in _iter_raw_token_ranges(cmd_line):
        raw_token = cmd_line[start:end]
        lexer = shlex.shlex(raw_token, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        value = lexer.get_token()
        if not value:
            continue

        token_start, token_end = start, end
        if _is_single_quoted_token(raw_token):
            token_start += 1
            token_end -= 1

        tokens.append(Token(value=value, start=token_start, end=token_end, index=len(tokens)))

    return tokens


if __name__ == "__main__":
    cmd = 'mycmd --input=abc --flag --output `somefile.txt` --input "some  file.txt"'
    tokens = tokenize(cmd)

    InterpretedInput.from_tokens(tokens, BooleanOptions(names=[]))

    for t in tokens:
        print(f"[{t.index}] '{t.value}' ({t.start}-{t.end})", cmd[t.start : t.end])
