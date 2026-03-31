from typing import Sequence, Any
from pytoy.shared.command.models import CommandModel, InjectedParam   
from pytoy.shared.command.tokenizer import tokenize, InterpretedInput, ResolvedInput  


class CommandExecutor:
    def __init__(self, ):
        pass

    def execute(self, command_model: CommandModel, command_line: str, injected_params: Sequence[InjectedParam]) -> Any:
        tokens = tokenize(command_line)
        interp = InterpretedInput.from_tokens(tokens, command_model)
        resolved_input = ResolvedInput.from_interpurted_input(command_model, interp)
        return self._invoke(command_model, resolved_input, injected_params)


    def _invoke(self, command_model: CommandModel, resolved_input: ResolvedInput, injected_params: Sequence[InjectedParam]) -> Any:
        args = resolved_input.args   
        kwargs = resolved_input.kwargs

        injected_mapping: dict[str, InjectedParam] = dict()
        cls_to_param = {type(param): param for param in injected_params}
        for name, cls in command_model.injected_params.items():
            injected_mapping[name] = cls_to_param[cls]
        return command_model.impl(*args, **dict(**kwargs, **injected_mapping))

