try:
    from pytoy.infra.sub_commands.specs import (
        ArgumentSpec,
        OptionSpec,
        Completion,
        SubCommandSpec,
        MainCommandSpec,
        CompletionContext,
        ContextType,
        ParsedArguments,
    )  # noqa
    from pytoy.infra.sub_commands.completion_context_maker import CompletionContextMaker
    from pytoy.infra.sub_commands.completion_provider import CompletionProvider
    from pytoy.infra.sub_commands.parse_provider import ParseProvider
except ImportError:
    from specs import (
        ArgumentSpec,
        OptionSpec,
        Completion,
        SubCommandSpec,
        MainCommandSpec,
        CompletionContext,
        ContextType,
        ParsedArguments,
    )  # noqa
    from completion_context_maker import CompletionContextMaker
    from completion_provider import CompletionProvider
    from pytoy.infra.sub_commands.parse_provider import ParseProvider


class SubCommandsHandler:
    """Handle interpretation and completion of `cmd_line`."""

    def __init__(self, main_spec: MainCommandSpec):
        self._main_spec = main_spec
        self.completion_provider = CompletionProvider(main_spec)
        self.parse_provider = ParseProvider(main_spec)

    @property
    def main_spec(self) -> MainCommandSpec:
        return self._main_spec

    def complete(self, arg_lead: str, cmd_line: str, cursor_pos: int) -> list[str]:
        return self.completion_provider(arg_lead, cmd_line, cursor_pos)

    def parse(self, cmd_line: str) -> ParsedArguments:
        return self.parse_provider(cmd_line)


if __name__ == "__main__":
    pass
