from pytoy.job_execution.command_executor.models import ExecutionHooks, ExecutionResult, PostProcessContext
from pytoy.shared.ui.pytoy_quickfix import PytoyQuickfix, QuickfixCreator, QuickfixRecordRegex


from dataclasses import dataclass
from typing import Literal, assert_never


@dataclass(frozen=True)
class QuickfixProfile:
    quickfix_creator: QuickfixCreator | QuickfixRecordRegex
    quickfix_source: Literal["stdout", "stderr", "both", "auto"] = "auto"

    @property
    def execution_hooks(self) -> ExecutionHooks:
        return make_quickfix_hooks(self)


def make_quickfix_hooks(quickfix_profile: QuickfixProfile) -> ExecutionHooks:
    from pytoy.shared.ui.pytoy_quickfix import to_quickfix_creator

    quickfix_creator = to_quickfix_creator(quickfix_profile.quickfix_creator)

    def _decide_quickfix_source(result: ExecutionResult, quickfix_profile: QuickfixProfile):
        match quickfix_profile.quickfix_source:
            case "stdout":
                return result.stdout
            case "stderr":
                return result.stderr
            case "both":
                return result.stdout + "\n\n" + result.stderr
            case "auto":
                return result.stderr if result.stderr else result.stdout
            case _:
                assert_never(quickfix_profile.quickfix_source)

    def on_post_process(post_process_context: PostProcessContext):
        result = post_process_context.result
        execution = post_process_context.execution
        quickfix_source = _decide_quickfix_source(result, quickfix_profile)
        records = quickfix_creator(quickfix_source, execution.cwd)
        PytoyQuickfix().handle_records(records, is_open=True)

    quickfix_hooks = ExecutionHooks(on_post_process=on_post_process)

    return quickfix_hooks
