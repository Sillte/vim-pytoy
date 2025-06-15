from pytoy.command import CommandManager

from pytoy.ui_pytoy.vscode.api import Api
from pytoy.ui_pytoy.vscode.document import Api, Uri, Document, get_uris
from pytoy.ui_pytoy.vscode.document_user import sweep_editors
from pytoy.timertask_manager import TimerTaskManager  
import vim


def script():
    jscode = """
    (async () => {
    await vscode.commands.executeCommand('workbench.action.focusNextGroup');
    const sleep = (time) => new Promise((resolve) => setTimeout(resolve, time));
    //await sleep(10)
    })()
    """
    return jscode
    pass


@CommandManager.register(name="CMD")
class CommandFunctionClass:
    name = "CMD"
    def __call__(self, cmd: str):
        from pytoy.executors import BufferExecutor
        from pytoy import TERM_STDOUT
        import os
        from pathlib import Path
        from pytoy.environment_manager import EnvironmentManager
        env = dict(os.environ)

        executor = BufferExecutor(name="CMD")
        cwd = str(vim.eval("getcwd()"))

        from pytoy.ui_pytoy import make_buffer
        
        if cmd.find("'") != -1:
            raise ValueError("This is yet mock, so `'` is not handled correctly.")

        pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")

        in_cmd = (
            "python -X utf8 -c \"import subprocess; "
            rf"print(subprocess.run('cmd /c {cmd} ', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=\"cp932\").stdout)"
            "\""
        )
        command = in_cmd.replace("'", "''")

        def init_buffers(wrapped, stdout, stderr):
            line = f"""$$$-------------------------------------------------------------------
{Path(cwd).as_posix()}
{cmd}
-------------------------------------------------------------------
""".strip()
            _ = command 
            _ = stderr
            stdout.append(line)

        executor.init_buffers = init_buffers

        wrapper = EnvironmentManager().get_command_wrapper(force_uv=False)
        executor.run(command, pytoy_buffer, pytoy_buffer, command_wrapper=wrapper, cwd=cwd, env=env)


