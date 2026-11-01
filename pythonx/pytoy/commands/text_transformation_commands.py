import os
import platform
import subprocess
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Literal

from pytoy.shared.command import App, Argument, Option
from pytoy.shared.timertask.thread_execution import ThreadExecutionHandler, ThreadExecutionHooks, ThreadExecutionRequest
from pytoy.shared.ui import PytoyBuffer, make_buffer
from pytoy.tools.text_transformation_plugin import TextTransformationHandler

app = App()
ConflictPolicy = Literal["preserve", "overwrite"]
_OUTPUT_BUFFER = "__text_transformation_output__"


def _complete_transformation_names() -> tuple[str, ...]:
    return TextTransformationHandler.from_global_folder().names


def _show_output(content: str) -> None:
    output_buffer = make_buffer(_OUTPUT_BUFFER, "vertical")
    output_buffer.init_buffer(content)


def _open_folder_in_file_manager(folder: Path) -> None:
    operating_system = platform.system()
    if operating_system == "Windows":
        os.startfile(str(folder))  # ty: ignore
    elif operating_system == "Darwin":
        subprocess.Popen(["open", str(folder)])
    elif operating_system == "Linux":
        subprocess.Popen(["xdg-open", str(folder)])
    else:
        raise OSError(f"Opening folders is not supported on {operating_system}.")


def _apply_result(
    buffer: PytoyBuffer,
    original_content: str,
    transformed_content: str,
    on_conflict: ConflictPolicy,
    show_output: Callable[[str], None],
) -> None:
    if not buffer.valid or not buffer.is_normal_type:
        show_output(
            "The source buffer is no longer available or editable. Transformation result:\n\n" + transformed_content
        )
        return

    if buffer.content != original_content and on_conflict == "preserve":
        show_output(
            "The source buffer changed during transformation. It was left unchanged. Result:\n\n" + transformed_content
        )
        return

    buffer.init_buffer(transformed_content)


@app.command("TextTransform")
def transform_buffer(
    name: Annotated[str, Argument(completer=_complete_transformation_names)],
    on_conflict: Annotated[ConflictPolicy, Option(default="preserve")] = "preserve",
) -> None:
    if on_conflict not in {"preserve", "overwrite"}:
        raise ValueError(f"Invalid conflict policy: {on_conflict!r}")

    buffer = PytoyBuffer.get_current()
    original_content = buffer.content

    def transform() -> str:
        handler = TextTransformationHandler.from_global_folder()
        return handler.transform(name, original_content)

    def on_result(transformed_content: str) -> None:
        _apply_result(buffer, original_content, transformed_content, on_conflict, _show_output)

    def on_exception(error: Exception) -> None:
        _show_output(f"Text transformation {name!r} failed:\n\n{''.join(traceback.format_exception(error))}")

    request = ThreadExecutionRequest.from_any(transform)
    hooks = ThreadExecutionHooks(on_result=on_result, on_exception=on_exception)
    ThreadExecutionHandler.create(request).start(hooks=hooks)


@app.command("TextTransformExample")
def create_text_transformation_example() -> None:
    handler = TextTransformationHandler.from_global_folder()
    example_path = handler.plugin_directory / "example.py"
    if handler.dump_default_examples():
        _show_output(f"Created example plugin: {example_path}")
    else:
        _show_output(f"Example plugin already exists; left unchanged: {example_path}")


@app.command("TextTransformOpenFolder")
def open_text_transformation_plugin_folder() -> None:
    try:
        folder = TextTransformationHandler.from_global_folder().plugin_directory
        _open_folder_in_file_manager(folder)
    except Exception:
        _show_output(traceback.format_exc())
    else:
        _show_output(f"Opened text transformation plugin folder:\n{folder}")
