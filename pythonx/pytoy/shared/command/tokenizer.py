from dataclasses import dataclass, field
from collections import defaultdict
from typing import Sequence, Mapping, Any, Self, get_args, get_origin
from collections.abc import Sequence as ABCSequence
import shlex
import re
from pytoy.shared.command.models import BooleanOptions, CommandModel, MISSING_DEFAULT, Token


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
    exceptions: Sequence[Exception] =  field(default_factory=list)

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

                options[key].append(str_val)
            else:
                arguments.append(token.value)
            i += 1
        return cls(arguments=arguments, options=options, exceptions=exceptions)


@dataclass(frozen=True)
class ResolvedInput:
    arg_kwargs: Mapping[str, Any]
    kwargs: Mapping[str, Any]

    @classmethod
    def _convert_element(
        cls, val: Any, element_types: Sequence[type] | set[type], literal_values: Sequence[Any] | None, only_literal: bool = False
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
        required_arguments = [elem for elem in command_model.arguments if elem.required]
        non_required_arguments =  [elem for elem in command_model.arguments if not elem.required]

        if len(interpreted_input.arguments) < len(required_arguments):
            raise ValueError("Too little arguments")
        given_arguments = required_arguments + non_required_arguments[:len(interpreted_input.arguments) - len(required_arguments)]
        non_given_arguments =  non_required_arguments[len(interpreted_input.arguments) - len(required_arguments):]
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
                origin = get_origin(typ)
                is_sequence = origin in (list, ABCSequence) and typ is not str
                if is_sequence:
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


def tokenize(cmd_line: str) -> list[Token]:
    """文字列をトークン化し、元文字列上の start/end 位置も保持する"""
    lexer = shlex.shlex(cmd_line, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""

    tokens = []
    current_pos = 0
    index = 0

    for token_str in lexer:
        if not token_str:
            continue

        # 正規表現で元文字列から token_str を検索（current_pos 以降）
        pattern = re.escape(token_str)
        match = re.search(pattern, cmd_line[current_pos:])
        if not match:
            break
        start_pos = current_pos + match.start()
        end_pos = start_pos + len(token_str)

        tokens.append(Token(value=token_str, start=start_pos, end=end_pos, index=index))
        current_pos = end_pos
        index += 1

    return tokens


if __name__ == "__main__":
    cmd = 'mycmd --input=abc --flag --output `somefile.txt` --input "some  file.txt"'
    tokens = tokenize(cmd)

    InterpretedInput.from_tokens(tokens, BooleanOptions(names=[]))

    for t in tokens:
        print(f"[{t.index}] '{t.value}' ({t.start}-{t.end})", cmd[t.start : t.end])
