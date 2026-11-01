from pytoy_llm.task.execution.models import TaskExecutionExit
from pytoy_llm.task.models import TaskCanceledException, TaskContextState, TaskResult
from pytoy_llm.task.shared.outcome import Error as TaskError
from pytoy_llm.task.shared.outcome import Success as TaskSuccess

from pytoy.shared.lib.outcome import is_error, is_success
from pytoy.tool_execution.llm.factory import transform


def test_transform_preserves_success_result() -> None:
    task_result = TaskResult(input="input", output="output", context_state=TaskContextState())
    task_exit = TaskExecutionExit(id="task-id", outcome=TaskSuccess(value=task_result))

    llm_exit = transform(task_exit)

    assert llm_exit.id == "task-id"
    assert is_success(llm_exit.outcome)
    assert llm_exit.outcome.value.output == "output"


def test_transform_preserves_task_exception() -> None:
    exception = TaskCanceledException()
    task_exit = TaskExecutionExit(id="task-id", outcome=TaskError(exception=exception))

    llm_exit = transform(task_exit)

    assert llm_exit.id == "task-id"
    assert is_error(llm_exit.outcome)
    assert llm_exit.outcome.exception is exception
