from dataclasses import dataclass, field
from enum import Enum
from typing  import Callable, Type


try:
    from pytoy.infra.sub_commands.tokenizer import Token
except ImportError:
    from tokenizer import Token


Completion = list[str] | Callable[[], list[str]]

OptionType = str | int | float | bool


@dataclass
class ArgumentSpec:
    name: str
    completion: Completion | None = None
    description: str = ""



class _DefaultSentinel:
    def __repr__(self):
        return "DEFAULT"
DEFAULT = _DefaultSentinel()

@dataclass
class OptionSpec:
    name: str  # This becomes the key to get value.
    type: Type[OptionType] = str
    aliases: list[str] = field(default_factory=list)  # the different names.
    short_option: str | None =  None  # short option
    completion: Completion | None = None # used for completion
    expects_value: bool = False
    description: str = ""
    default: OptionType | None | _DefaultSentinel = DEFAULT


@dataclass
class SubCommandSpec:
    name: str
    argument: ArgumentSpec | None = None
    options: list[OptionSpec] = field(default_factory=list)
    description: str = ""


@dataclass
class MainCommandSpec:
    commands: list[SubCommandSpec]
    options: list[OptionSpec] = field(default_factory=list)
    description: str = ""


class ContextType(str, Enum):
    SUB_COMMAND = "COMMAND"
    OPTION_KEY = "OPTION_KEY"
    OPTION_VALUE = "OPTION_VALUE"
    OPTION_KEY_AND_VALUE = "OPTION_KEY_AND_VALUE"
    ARGUMENT = "ARGUMENT"

    NOCMP = "NOCMP"


@dataclass(frozen=True)
class CompletionContext:
    completion_type: ContextType
    tokens: list[Token]  # ['MyCmd', '--input=abc', '--fl']
    current_token: Token | None  # '--fl'
    option_name: str | None = None  # The target option names.
    sub_command: str | None = (
        None  # The context of current command, if `None`, it is main_option.
    )


@dataclass(frozen=True)
class ParsedArguments:
    """Result of parsed `cmd_line`."""

    sub_command: str | None
    main_options: dict[str, OptionType | None]
    main_arguments: list[str]
    sub_options: dict[str, OptionType | None]
    sub_arguments: list[str]
