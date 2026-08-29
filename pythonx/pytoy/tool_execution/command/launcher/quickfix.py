from dataclasses import dataclass
from typing import Literal, assert_never

from pytoy.shared.ui.pytoy_quickfix import PytoyQuickfix, QuickfixCreator, QuickfixRecordRegex
from pytoy.tool_execution.command.models import (
    CommandExecutionHooks,
    CommandExecutionResult,
)


@dataclass(frozen=True)
class QuickfixProfile:
    quickfix_creator: QuickfixCreator | QuickfixRecordRegex
    quickfix_source: Literal["stdout", "stderr", "both", "auto"] = "auto"

    @property
    def execution_hooks(self) -> CommandExecutionHooks:
        return make_quickfix_hooks(self)


def make_quickfix_hooks(quickfix_profile: QuickfixProfile) -> CommandExecutionHooks:
    from pytoy.shared.ui.pytoy_quickfix import to_quickfix_creator

    quickfix_creator = to_quickfix_creator(quickfix_profile.quickfix_creator)

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
        records = quickfix_creator(quickfix_source, result.cwd)
        PytoyQuickfix().handle_records(records, is_open=False)

    quickfix_hooks = CommandExecutionHooks(on_result=on_post_process)

    return quickfix_hooks
