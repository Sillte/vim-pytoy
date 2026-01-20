from typing import Sequence, Mapping
import vim
from pytoy.lib_tools.command_executor import ExecutionRequest, ExecutionHooks, ExecutionResult,  BufferRequest 
from pytoy.lib_tools.command_executor import CommandExecutor, CommandExecution
from pytoy.ui.pytoy_quickfix import PytoyQuickfix
from pytoy.contexts.pytoy import GlobalPytoyContext
from dataclasses import dataclass 

from pytoy.ui.pytoy_quickfix import to_quickfix_creator, QuickfixCreator, QuickfixRecordRegex, QuickfixRecord
from pathlib import Path 

@dataclass
class QuickfixCommandRequest:
    execution: ExecutionRequest
    creator: QuickfixCreator| QuickfixRecordRegex


def handle_records(
    pytoy_quickfix: PytoyQuickfix,
    records: Sequence[QuickfixRecord],
    is_open: bool = True,
):
    """When `records` are given, `PytoyQuickFix`  handles them."""
    # TODO: This is not good one, 
    # Once the mechanism of `QuickFix` for `LocationList` (winid), 
    # the 
    if records:
        pytoy_quickfix.set_records(records)
        if is_open:
            PytoyQuickfix().open()
    else:
        PytoyQuickfix().close()


class QuickfixCommandExecutor:
    def __init__(self, buffer_request: BufferRequest | None = None, hooks: ExecutionHooks | None = None,
                  *, ctx: GlobalPytoyContext | None = None):
        if buffer_request is None:
            buffer_request = BufferRequest.from_str("__pytoy_stdout__")
        if hooks is None:
            hooks = ExecutionHooks()
        self._hooks = hooks

        self._executor = CommandExecutor(buffer_request=buffer_request, ctx=ctx)
    
    @property
    def command_executor(self) -> CommandExecutor:
        return self._executor

    def execute(self, command_request: QuickfixCommandRequest, *, init_buffer: bool = True) -> CommandExecution:
        execution_request = command_request.execution
        
        def _on_start(execution: CommandExecution) -> None:
            command: str = str(execution.command)
            self._executor.stdout.append(command)
            
        def _on_finish(result: ExecutionResult) -> None:
            creator = to_quickfix_creator(command_request.creator, execution.cwd)
            records = creator(result.stdout)
            handle_records(PytoyQuickfix(), records)
        
        q_hooks = ExecutionHooks(on_start=_on_start, on_finish=_on_finish)
        hooks = ExecutionHooks.merge(self._hooks, q_hooks)
        execution =  self._executor.execute(execution_request, hooks=hooks, init_buffer=init_buffer)
        return execution
    
if __name__ == "__main__":
    # 2. 実行リクエストの作成
    # 以前作った uv_wrapper を通すために command_wrapper="auto" を指定
    request = ExecutionRequest(
        command=["ruff", "check", ".", "--output-format=concise"],
        cwd=Path.cwd(),
        command_wrapper="auto"  # これで自動的に 'uv run' が付与される
    )

    # 3. QuickFixCommandRequest にまとめる
    qf_request = QuickfixCommandRequest(
        execution=request,
        creator=r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+):(?P<text>(.+))"
    )

    # 4. 実行
    executor = QuickfixCommandExecutor()
    execution = executor.execute(qf_request)
    
