from pytoy.command import CommandManager
from pytoy.infra.command.models import OptsArgument


@CommandManager.register(name="ToolChainSelect")
class ToolChainSelect:
    """Select the Runner"""

    def __init__(self):
        self._environment_manager = None
    
    @property
    def environment_manager(self):
        if self._environment_manager:
            return self._environment_manager
        from pytoy.contexts.core import GlobalCoreContext
        self._environment_manager = GlobalCoreContext.get().environment_manager
        return self._environment_manager


    def __call__(self, opts: OptsArgument):
        manager =  self.environment_manager
        preferences = manager.available_execution_preferences
        farg = opts.fargs[0] if opts.fargs else "auto"

        if farg in preferences:
            manager.set_execution_preference(farg)
        else:
            raise ValueError(f"`{farg=}` is not valid execution preference")

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        """This is defined by `Command`."""
        prefs = self.environment_manager.available_execution_preferences
        result  = [elem for elem in prefs if elem.startswith(arg_lead)]
        return result


