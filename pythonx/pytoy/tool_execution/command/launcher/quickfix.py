from dataclasses import dataclass
from typing import Literal, assert_never

from pytoy.shared.ui.pytoy_quickfix import Quickfix, QuickfixRecordsCreatorLike
from pytoy.tool_execution.command.models import (
    CommandExecutionHooks,
    CommandExecutionResult,
)


@dataclass(frozen=True)
class QuickfixProfile:
    quickfix_creator: QuickfixRecordsCreatorLike
    quickfix_source: Literal["stdout", "stderr", "both", "auto"] = "auto"

    @property
    def execution_hooks(self) -> CommandExecutionHooks:
        return make_quickfix_hooks(self)


def make_quickfix_hooks(quickfix_profile: QuickfixProfile) -> CommandExecutionHooks:
    from pytoy.shared.ui.pytoy_quickfix import QuickfixRecordsCreator

    records_creator = QuickfixRecordsCreator.from_any(quickfix_profile.quickfix_creator)

    def _decide_quickfix_source(result: CommandExecutionResult, quickfix_profile: QuickfixProfile):
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

    def on_post_process(result: CommandExecutionResult):
        quickfix_source = _decide_quickfix_source(result, quickfix_profile)
        records = records_creator.create(quickfix_source, result.cwd)
        Quickfix.from_any(records, try_reuse=True, working_directory=result.cwd)

    quickfix_hooks = CommandExecutionHooks(on_result=on_post_process)

    return quickfix_hooks
