from pytoy.shared.command import Argument, App
from typing import Literal, Annotated

app = App()


@app.command("ToolChainSelect")
def tool_chain_select(arg: Annotated[Literal["auto", "uv", "system"], Argument()] = "auto"):

    from pytoy.contexts.core import GlobalCoreContext

    environment_manager = GlobalCoreContext.get().environment_manager

    preferences = environment_manager.available_execution_preferences

    if arg in preferences:
        environment_manager.set_execution_preference(arg)
    else:
        raise ValueError(f"`{arg=}` is not valid execution preference")
