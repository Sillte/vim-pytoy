from threading import Event
from unittest.mock import Mock, patch

from pytoy.shared.timertask.routine_session import RoutineContext
from pytoy.tools.llm.idea_routine.handler import IdeaRoutineHandler


def test_worker_dispatches_llm_progress_from_result_hook() -> None:
    session_handler = Mock()
    routine_session_handler = Mock()

    with patch(
        "pytoy.tools.llm.idea_routine.handler.RoutineSessionHandler.create",
        return_value=routine_session_handler,
    ):
        IdeaRoutineHandler(session_handler, Mock())

    create_unit_kwargs = routine_session_handler.create_unit.call_args.kwargs
    worker = create_unit_kwargs["request"].worker
    on_result = create_unit_kwargs["hooks"].on_result

    worker(RoutineContext(cancel_token=Event(), unit_name="llm-invocation"))
    session_handler.make_progress.assert_not_called()

    on_result(None)
    session_handler.make_progress.assert_called_once_with("NON-USED INPUT")
