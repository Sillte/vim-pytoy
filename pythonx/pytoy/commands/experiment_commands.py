from pytoy.infra.command.models import OptsArgument
import vim
from pytoy.ui import make_buffer
from pytoy.command import CommandManager

from pytoy.lib_tools.terminal_backend.executor import TerminalExecutor


class CommandTerminal:
    name = "__CMD__"

    executor = None

    @staticmethod
    def get_executor():
        if CommandTerminal.executor:
            return CommandTerminal.executor

        from pytoy.lib_tools.terminal_backend import TerminalBackendProvider
        from pytoy.lib_tools.terminal_backend.application import ShellApplication

        from pytoy.lib_tools.terminal_backend.line_buffers import (
            LineBufferNaive,
        )

        app = ShellApplication()
        backend = TerminalBackendProvider().make_terminal(app, LineBufferNaive())
        buffer = make_buffer(CommandTerminal.name)
        executor = TerminalExecutor(buffer, backend)

        CommandTerminal.executor = executor
        return executor

    @CommandManager.register(name="CMD", range=True)
    @staticmethod
    def send(opts: OptsArgument):
        executor = CommandTerminal.get_executor()
        if not executor.alive:
            executor.start()

        # [NOTE]: this specification should be discussed.
        cmd = opts.args
        # if not cmd.strip():
        #    executor.interrupt()

        line1, line2 = opts.line1, opts.line2
        if not cmd.strip():
            lines = vim.eval(f"getline({line1}, {line2})")
            cmd = "\n".join(lines)

        executor.send(cmd)
