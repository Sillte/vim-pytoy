
class CommandWrapper:
    """Callable. modify the command you execute.
    Sometimes, we would like to change the environment
    where the command is executed.
    * not naive python, but the python of virtual environment.
    * not naive invocation, but with `uv run`.
    `CommandWrapper` handles this kind of request with depndency injection.
    """

    def __call__(self, cmd: str) -> str:
        return cmd
