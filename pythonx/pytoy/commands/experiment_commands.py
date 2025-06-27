import vim
import os
from pathlib import Path
from pytoy.environment_manager import EnvironmentManager
from pytoy.ui import make_buffer
from pytoy.command import CommandManager, OptsArgument 

from pytoy.buffer_executor import BufferExecutor
from pytoy import TERM_STDOUT


@CommandManager.register(name="CMD", range=True)
class CommandFunctionClass:
    def __call__(self, opts: OptsArgument):
        cmd = opts.args
        line1, line2 = opts.line1, opts.line2
        if not cmd.strip():
            cmd = vim.eval(f"getline({line1})")


        env = dict(os.environ)

        executor = BufferExecutor(name="CMD")
        cwd = str(vim.eval("getcwd()"))
        
        if cmd.find("'") != -1:
            raise ValueError("This is yet mock, so `'` is not handled correctly.")
        pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")

        in_cmd = (
            "python -X utf8 -c \"import subprocess; "
            rf"print(subprocess.run('{cmd}', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=\"cp932\", shell=True).stdout)"
            "\""
        )
        command = in_cmd.replace("'", "''")

        def init_buffers(wrapped, stdout, stderr):
            line = f"""###-------------------------------------------------------------------
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
