from dataclasses import dataclass, replace
from typing import Literal, Mapping, Sequence, assert_never

from pytoy.shared.command.core.models import ArgumentModel, BooleanOptions, CommandModel, OptionModel, Token
from pytoy.shared.command.core.tokenizer import InterpretedInput, OptionValueMissingError
from pytoy.shared.command.service.completion_lexer import CompletionInputToken, CompletionToken, tokenize_for_completion

# Input to the inside of the domain.


@dataclass(frozen=True)
class CompletionParam:
    """Input to completion.

    `cursor_pos` is a 0-based insertion index relative to `cmd_line`. `offset` is
    the character offset from the original command line to `cmd_line`; the
    service adds it to candidate ranges before returning them. For example, if
    the original line is `Demo --opti`, `cmd_line` is ` --opti`, and `offset` is
    4, a local candidate range `[1, 7)` becomes `[5, 11)`.
    """

    cmd_line: str
    cursor_pos: int  # Insertion position in [0, len(cmd_line)], relative to cmd_line.
    offset: int  # Shift applied to candidate ranges in the result.


@dataclass(frozen=True)
class TokenInterval:
    prev_token: Token
    prev_token_index: int


@dataclass(frozen=True)
class CursorTokenPosition:
    cursor_pos: int  # 0-based insertion index into the command line.
    prev_token: CompletionInputToken | None = None
    current_token: CompletionInputToken | None = None
    next_token: CompletionInputToken | None = None
    end_of_current_token: bool = False

    @property
    def beginning(self) -> bool:
        if self.current_token is None and self.prev_token is None:
            return True
        return False

    @property
    def last(self) -> bool:
        if self.current_token is None and self.next_token is None:
            return True
        return False


@dataclass(frozen=True)
class CmdlineStatus:
    cmd_line: str
    cursor_pos: int
    tokens: Sequence[CompletionInputToken]
    command_model: CommandModel

    @property
    def current_position(self) -> CursorTokenPosition:
        if not self.tokens:
            return CursorTokenPosition(
                cursor_pos=self.cursor_pos,
                prev_token=None,
                current_token=None,
                next_token=None,
                end_of_current_token=False,
            )

        first = self.tokens[0]
        if self.cursor_pos < first.start:
            return CursorTokenPosition(
                cursor_pos=self.cursor_pos,
                prev_token=None,
                current_token=None,
                next_token=first,
                end_of_current_token=False,
            )

        for i, token in enumerate(self.tokens):
            prev_token = self.tokens[i - 1] if i > 0 else None
            next_token = self.tokens[i + 1] if i + 1 < len(self.tokens) else None

            if token.start <= self.cursor_pos < token.end:
                return CursorTokenPosition(
                    cursor_pos=self.cursor_pos,
                    prev_token=prev_token,
                    current_token=token,
                    next_token=next_token,
                    end_of_current_token=False,
                )
            elif self.cursor_pos == token.end:
                return CursorTokenPosition(
                    cursor_pos=self.cursor_pos,
                    prev_token=prev_token,
                    current_token=token,
                    next_token=next_token,
                    end_of_current_token=True,
                )

            if next_token and self.cursor_pos < next_token.start:
                return CursorTokenPosition(
                    cursor_pos=self.cursor_pos,
                    prev_token=token,
                    current_token=None,
                    next_token=next_token,
                    end_of_current_token=False,
                )

        return CursorTokenPosition(
            cursor_pos=self.cursor_pos,
            prev_token=self.tokens[-1],
            current_token=None,
            next_token=None,
            end_of_current_token=False,
        )


@dataclass(frozen=True)
class ArgumentAppeal:
    argument: ArgumentModel
    type: Literal["Argument"] = "Argument"


@dataclass(frozen=True)
class OptionAppeal:
    options: Mapping[str, OptionModel]
    type: Literal["Option"] = "Option"


@dataclass(frozen=True)
class OptionValueAppeal:
    option: OptionModel
    type: Literal["OptionValue"] = "OptionValue"


type Appeal = ArgumentAppeal | OptionAppeal | OptionValueAppeal


class NextTokenResolver:
    def _resolve_exceptions(self, interp: InterpretedInput, command_model: CommandModel) -> Sequence[Appeal]:
        appeals = []
        option_map = {opt.name: opt for opt in command_model.options}

        # When the solvable exception exists, the highest priorty is to resove them.
        missing_keys = [elem.option_key for elem in interp.exceptions if isinstance(elem, OptionValueMissingError)]
        for key in missing_keys:
            if key in option_map:
                appeals.append(OptionValueAppeal(option=option_map[key]))
        return appeals

    def resolve_appeals(self, tokens: Sequence[Token], command_model: CommandModel) -> Sequence[Appeal]:
        interp = InterpretedInput.from_tokens(tokens, BooleanOptions.from_command_model(command_model))
        # When the solvable exception exists, the highest priorty is to resove them.
        appeals = self._resolve_exceptions(interp, command_model)
        if appeals:
            return appeals

        # Below, both of options and arguments are available.
        appeals = []

        n_used_arguments = len(interp.arguments)
        positional_argument_order = command_model.positional_argument_order
        if n_used_arguments < len(positional_argument_order):
            appeals.append(ArgumentAppeal(argument=positional_argument_order[n_used_arguments]))

        option_map = {opt.name: opt for opt in command_model.options}
        unused_keys = option_map.keys() - interp.options.keys()
        appeals.append(OptionAppeal(options={key: option_map[key] for key in unused_keys}))

        return appeals


# Output to the outside of the domain.


@dataclass(frozen=True)
class CompletionCandidate:
    """A completion value that replaces a half-open range in a command line.

    `start` and `end` are 0-based Python `str` indices, with `end` exclusive.
    CompletionService adds CompletionParam.offset to factory-local indices so
    returned ranges address the caller's command line.

    `kind` is optional classification metadata and currently does not affect
    completion behavior.
    """

    start: int
    end: int
    value: str
    kind: str | None = None


@dataclass(frozen=True)
class CompletionResult:
    candidates: Sequence[CompletionCandidate]


class CandidateFactory:
    def __init__(self):
        pass

    def _appeal_to_candidates(self, appeal: Appeal, leading: str, start: int, end: int) -> list[CompletionCandidate]:
        is_option = leading.startswith("-")

        leading = leading or ""

        match appeal.type:
            case "Argument":
                if is_option:
                    return []
                else:
                    candidates = appeal.argument.get_candidate_values()
                    candidates = [elem for elem in candidates if elem.startswith(leading)]
                    return [CompletionCandidate(start=start, end=end, value=elem) for elem in candidates]
            case "Option":
                if not is_option:
                    return []

                if leading.startswith("--"):
                    leading_key = leading[2:]
                    if leading_key.find("=") != -1:
                        leading_key, value = leading_key.split("=", 1)
                    else:
                        leading_key, value = leading_key, None
                else:
                    leading_key, value = None, None

                if leading_key and value is not None:
                    value = value or ""
                    if option := appeal.options.get(InterpretedInput.convert_key(leading_key)):
                        cands = option.get_candidate_values()
                        cands = [elem for elem in cands if elem.startswith(value)]
                        token_values = [f"--{leading_key}={cand}" for cand in cands]
                        return [
                            CompletionCandidate(start=start, end=end, value=token_value) for token_value in token_values
                        ]
                    else:
                        return []
                elif leading_key and value is None:
                    token_values = [
                        f"--{InterpretedInput.revert_key(key)}"
                        for key in appeal.options.keys()
                        if key.startswith(InterpretedInput.convert_key(leading_key))
                    ]
                    return [
                        CompletionCandidate(start=start, end=end, value=token_value) for token_value in token_values
                    ]
                else:
                    token_values = [f"--{InterpretedInput.revert_key(key)}" for key in appeal.options.keys()]
                    return [
                        CompletionCandidate(start=start, end=end, value=token_value) for token_value in token_values
                    ]

            case "OptionValue":
                cands = appeal.option.get_candidate_values()
                cands = [elem for elem in cands if elem.startswith(leading)]
                token_values = cands
                return [CompletionCandidate(start=start, end=end, value=token_value) for token_value in token_values]

            case _:
                assert_never(appeal)

    def create(
        self, position: CursorTokenPosition, appeals: Sequence[Appeal], command_model: CommandModel
    ) -> Sequence[CompletionCandidate]:

        current_token = position.current_token
        if not current_token:
            start = position.cursor_pos
            end = start
            leading = ""
        else:
            start = current_token.start
            end = current_token.end
            if isinstance(current_token, CompletionToken):
                leading = current_token.leading
            else:
                leading = current_token.value[: position.cursor_pos - current_token.start]
        candidates = []

        for appeal in appeals:
            candidates.extend(self._appeal_to_candidates(appeal, leading, start, end))

        if (
            isinstance(current_token, CompletionToken)
            and current_token.open_quote is not None
            and current_token.open_quote_value_start is not None
        ):
            logical_prefix = current_token.value[: current_token.open_quote_value_start]
            quote = current_token.open_quote
            quoted_candidates = []
            for candidate in candidates:
                if candidate.value.startswith(logical_prefix):
                    quote_index = len(logical_prefix)
                elif logical_prefix.startswith("--") and "=" in logical_prefix:
                    quote_index = candidate.value.find("=") + 1
                else:
                    quote_index = 0
                value = candidate.value[:quote_index] + quote + candidate.value[quote_index:]
                quoted_candidates.append(replace(candidate, value=value))
            candidates = quoted_candidates

        return self._to_unique(candidates)

    def _to_unique(self, candidates: Sequence[CompletionCandidate]) -> Sequence[CompletionCandidate]:
        return list({cand.value: cand for cand in candidates}.values())


class CompletionService:
    def __init__(self):
        pass

    def make_completions(self, command_model: CommandModel, completion_param: CompletionParam) -> CompletionResult:
        cmd_line = completion_param.cmd_line
        cursor_pos = completion_param.cursor_pos
        offset = completion_param.offset

        tokens = tokenize_for_completion(cmd_line, cursor_pos)
        status = CmdlineStatus(
            cmd_line=cmd_line,
            cursor_pos=cursor_pos,
            tokens=tokens,
            command_model=command_model,
        )

        current_position = status.current_position
        resolver = NextTokenResolver()

        complete_tokens = [token for token in tokens if isinstance(token, Token)]
        if current_position.current_token:
            prev_tokens = [token for token in complete_tokens if token.end < current_position.cursor_pos]
        else:
            prev_tokens = complete_tokens
        appeals = resolver.resolve_appeals(prev_tokens, command_model)

        factory = CandidateFactory()
        candidates = factory.create(current_position, appeals, command_model)

        # Resolve offsets.
        if offset != 0:
            candidates = [replace(cand, start=cand.start + offset, end=cand.end + offset) for cand in candidates]
        return CompletionResult(candidates=candidates)
