from typing import Sequence, Any
from pytoy.shared.command.core.models import CommandModel, InjectedParam   
from pytoy.shared.command.core.tokenizer import tokenize, InterpretedInput, ResolvedInput  


class ExecutionService:
    def __init__(self, ):
        pass

    def execute(self, command_model: CommandModel, command_line: str, injected_params: Sequence[InjectedParam]) -> Any:
        tokens = tokenize(command_line)
        interp = InterpretedInput.from_tokens(tokens, command_model)
        resolved_input = ResolvedInput.from_interpreted_input(command_model, interp)
        return self._invoke(command_model, resolved_input, injected_params)


    def _invoke(self, command_model: CommandModel, resolved_input: ResolvedInput, injected_params: Sequence[InjectedParam]) -> Any:
        arg_kwargs = resolved_input.arg_kwargs   
        kwargs = resolved_input.kwargs

        injected_mapping: dict[str, InjectedParam] = dict()
        cls_to_param = {type(param): param for param in injected_params}
        for name, cls in command_model.injected_params.items():
            injected_mapping[name] = cls_to_param[cls]
        return command_model.impl(**dict(**arg_kwargs, **kwargs, **injected_mapping))

