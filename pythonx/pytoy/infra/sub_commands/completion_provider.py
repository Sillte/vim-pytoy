try:
    from pytoy.infra.sub_commands.specs import (
        ArgumentSpec,
        OptionSpec,
        Completion,
        SubCommandSpec,
        MainCommandSpec,
        CompletionContext,
        ContextType,
    )
    from pytoy.infra.sub_commands.completion_context_maker import CompletionContextMaker
except ImportError:
    from specs import (
        OptionSpec,
        Completion,
        MainCommandSpec,
        CompletionContext,
        ContextType,
    )
    from pytoy.infra.sub_commands.completion_context_maker import CompletionContextMaker


class _OptionCandidatesProvider:
    def __init__(self, main_spec: MainCommandSpec, context: CompletionContext):
        self.main_spec = main_spec
        self.context = context

    def __call__(self, arg_lead: str, cmd_line: str, cursor_pos: int) -> list[str]:
        _ = cmd_line
        _ = cursor_pos
        sub_command = self.context.sub_command
        name_to_option = self._get_options(sub_command)
        if self.context.completion_type == ContextType.OPTION_KEY:
            candidates = [f"--{name}" for name in name_to_option]
            return self._candidates_to_result(arg_lead, candidates)
        elif self.context.completion_type == ContextType.OPTION_VALUE:
            option_name = self.context.option_name
            if option_name not in name_to_option:
                return [arg_lead]
            candidates = self._from_completion(name_to_option[option_name].completion)
            return self._candidates_to_result(arg_lead, candidates)
        elif self.context.completion_type == ContextType.OPTION_KEY_AND_VALUE:
            option_name = self.context.option_name
            if option_name not in name_to_option:
                return [arg_lead]
            stem_candidates = self._from_completion(
                name_to_option[option_name].completion
            )
            if not stem_candidates:
                return [arg_lead]
            candidates = [f"--{option_name}={value}" for value in stem_candidates]
            return self._candidates_to_result(arg_lead, candidates)
        raise ValueError("Invalid in _OptionCandidatesProvider")

    def _get_options(self, sub_name: str | None) -> dict[str, OptionSpec]:
        if sub_name is None:
            return {option.name: option for option in self.main_spec.options}
        name_to_subcommand = {
            sub_command.name: sub_command for sub_command in self.main_spec.commands
        }
        sub_command = name_to_subcommand[sub_name]
        return {option.name: option for option in sub_command.options}

    def _from_completion(self, completion: None | Completion) -> None | list[str]:
        if completion is None:
            return None
        if isinstance(completion, list):
            return completion
        return completion()

    def _candidates_to_result(
        self, arg_lead: str, candidates: list[str] | None
    ) -> list[str]:
        if not candidates:
            return [arg_lead]
        valid_candidates = [elem for elem in candidates if elem.startswith(arg_lead)]
        if valid_candidates:
            return valid_candidates
        return candidates


class _ArgumentCandidatesProvider:
    def __init__(self, main_spec: MainCommandSpec, context: CompletionContext):
        self.main_spec = main_spec
        self.context = context

    def __call__(self, arg_lead: str, cmd_line: str, cursor_pos: int) -> list[str]:
        _ = cmd_line
        _ = cursor_pos
        sub_name = self.context.sub_command

        if sub_name is None:
            return [arg_lead]

        name_to_subcommand = {
            sub_command.name: sub_command for sub_command in self.main_spec.commands
        }
        sub_command = name_to_subcommand[sub_name]
        if not sub_command.argument:
            return [arg_lead]
        candidates = self._from_completion(sub_command.argument.completion)
        return self._candidates_to_result(arg_lead, candidates)

    def _from_completion(self, completion: None | Completion) -> None | list[str]:
        if completion is None:
            return None
        if isinstance(completion, list):
            return completion
        return completion()

    def _candidates_to_result(
        self, arg_lead: str, candidates: list[str] | None
    ) -> list[str]:
        if not candidates:
            return [arg_lead]
        valid_candidates = [elem for elem in candidates if elem.startswith(arg_lead)]
        if valid_candidates:
            return valid_candidates
        return candidates


def _remove_range(cmd_line: str, cursor_pos: int) -> tuple[str, int]:
    """Return the `cmd_line`, whose `range` is trimmed and modified `

    Example,
    --------
    '<,'>Command -> Command
    10,'>Command -> Command
    """
    for i, c in enumerate(cmd_line):
        if c.isalpha():
            return cmd_line[i:], cursor_pos - i
    return cmd_line, cursor_pos


class CompletionProvider:
    def __init__(self, command_spec: MainCommandSpec):
        self._main_command_spec = command_spec

    @property
    def main_spec(self) -> MainCommandSpec:
        return self._main_command_spec

    def __call__(self, arg_lead: str, cmd_line: str, cursor_pos: int) -> list[str]:
        cmd_line, cursor_pos = _remove_range(cmd_line, cursor_pos)

        # Here, `cmd_line` starts the command like `Command ...`
        context_maker = CompletionContextMaker(self.main_spec)
        context = context_maker(arg_lead, cmd_line, cursor_pos)

        if context.completion_type in {
            ContextType.OPTION_KEY,
            ContextType.OPTION_VALUE,
            ContextType.OPTION_KEY_AND_VALUE,
        }:
            option_provider = _OptionCandidatesProvider(self.main_spec, context)
            return option_provider(arg_lead, cmd_line, cursor_pos)
        elif context.completion_type == ContextType.SUB_COMMAND:
            candidates = [sub_command.name for sub_command in self.main_spec.commands]
            return candidates if candidates else [arg_lead]
        elif context.completion_type == ContextType.ARGUMENT:
            argument_provider = _ArgumentCandidatesProvider(self.main_spec, context)
            return argument_provider(arg_lead, cmd_line, cursor_pos)
        return [arg_lead]
