from pytoy.infra.sub_commands.tokenizer import Token, tokenize
from pytoy.infra.sub_commands.specs import (
    ArgumentSpec,
    OptionSpec,
    Completion,
    SubCommandSpec,
    MainCommandSpec,
    CompletionContext,
    ContextType,
)



class CompletionContextMaker:
    def __init__(self, main_spec: MainCommandSpec) -> None:
        self.main_spec = main_spec

    def __call__(self, arg_lead: str, cmd_line: str, cursor_pos: int) -> CompletionContext:
        _ = arg_lead
        tokens = tokenize(cmd_line)
        sub_command_token, current_token, prev_token = self._fetch_pivot_tokens(
            tokens, cursor_pos
        )

        if len(tokens) == 1 and self.main_spec.commands:
            return CompletionContext(ContextType.SUB_COMMAND, tokens, current_token)

        if not current_token:
            return CompletionContext(ContextType.NOCMP, tokens, current_token)

        sub_command = sub_command_token.value if sub_command_token else None

        # Options for `main` command.
        if sub_command_token is None or current_token.index < sub_command_token.index:
            context = self._make_option_context(
                self.main_spec, current_token, prev_token, tokens, sub_command=None
            )
            if context:
                return context
            if sub_command is None:
                return CompletionContext(ContextType.SUB_COMMAND, tokens, current_token)
            else:
                return CompletionContext(ContextType.NOCMP, tokens, current_token)

        # Options for `sub_command`.
        sub_tokens = [
            token for token in tokens if sub_command_token.index < token.index
        ]
        if not sub_tokens:
            return CompletionContext(ContextType.NOCMP, tokens, current_token)

        context = self._make_option_context(
            self.main_spec, current_token, prev_token, tokens, sub_command=sub_command
        )
        if context:
            return context
        return CompletionContext(ContextType.ARGUMENT, tokens, current_token)

    def _fetch_pivot_tokens(
        self, tokens: list[Token], cursor_pos: int
    ) -> tuple[Token | None, Token | None, Token | None]:
        """Return (subcommand_token, current_token, prev_token)"""
        # tokens[0] should be the `name` of main_spec`
        tokens = tokens[1:]

        sub_names = set(command.name for command in self.main_spec.commands)
        sub_command_token = None
        for token in tokens:
            if token.value in set(sub_names):
                sub_command_token = token

        prev_token = None
        current_token = None
        for token in tokens:
            if token.is_current_token(cursor_pos):
                current_token = token
                break
            prev_token = token
        return (sub_command_token, current_token, prev_token)

    def _make_option_context(
        self,
        main_spec: MainCommandSpec,
        current_token: Token,
        prev_token: Token | None,
        tokens: list[Token],
        sub_command: str | None,
    ) -> None | CompletionContext:
        opt_name, opt_value = self._token_to_opt(current_token)
        if opt_name and (opt_value is not None):
            return CompletionContext(
                ContextType.OPTION_KEY_AND_VALUE,
                tokens,
                current_token,
                opt_name,
                sub_command=sub_command,
            )
        if opt_name is not None:
            return CompletionContext(
                ContextType.OPTION_KEY, tokens, current_token, sub_command=sub_command
            )

        if prev_token:
            opt_name, opt_value = self._token_to_opt(prev_token)
            if opt_value is None:  # Already `value` is fixed.
                name_to_opt = {opt.name: opt for opt in main_spec.options}
                if opt_name in name_to_opt:
                    if name_to_opt[opt_name].expects_value:
                        return CompletionContext(
                            ContextType.OPTION_VALUE,
                            tokens,
                            current_token,
                            opt_name,
                            sub_command=sub_command,
                        )
        return None

    def _token_to_opt(self, token: Token) -> tuple[str | None, str | None]:
        """If `token` is related to `Option`,
        then it returns the key and value."""
        if not token.value.startswith("-"):
            return (None, None)
        elif token.value.startswith("--"):
            pos = token.value.find("=")
            if pos == -1:
                return (token.value.strip("--"), None)
            opt_key, opt_value = token.value.split("=", 1)
            return (opt_key.strip("-"), opt_value)
        elif token.value.startswith("-"):
            return (token.value.strip("-"), None)
        return (None, None)


if __name__ == "__main__":
    pass
