from typing import Annotated

from pytoy.shared.command import App, Option
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer, make_buffer
from pytoy.shared.ui.pytoy_window import PytoyWindow

app = App()


@app.command("GatherTextFiles")
def gather_text_files(
    depth: Annotated[int | None, Option(default=None)], pattern: Annotated[str | None, Option(default=None)]
):
    from pytoy_llm.composers.materials import MaterialDataExplorerTaskComposer
    from pytoy_llm.materials.text_files import TextFilesCollector, TextFilesMaterialQuery

    from pytoy.tool_execution.execution_environment import EnvironmentManager

    buffer = PytoyBuffer.get_current()
    if not buffer.is_file:
        raise ValueError("Target buffer is not file.")
    path = buffer.file_path
    workspace = EnvironmentManager().find_workspace(path, preference="system")
    workspace = workspace or path.parent
    if not pattern:
        pattern = f"*{path.suffix}"

    query = TextFilesMaterialQuery.from_any(collection_root=path, patterns=[pattern], max_depth=depth, only_meta=False)
    material = TextFilesCollector(workspace=workspace).get_material(query)
    composer = MaterialDataExplorerTaskComposer([material.text_material_data])
    section_text = composer.compose_system_prompt()
    buffer = make_buffer("__docs__", "vertical")
    buffer.init_buffer()
    buffer.append(section_text)


@app.command("GatherGitDiffs")
def gather_git_diffs():
    from pathlib import Path

    from pytoy_llm.composers.materials import MaterialDataExplorerTaskComposer
    from pytoy_llm.materials.git_diffs.collectors import GitDiffCollector
    from pytoy_llm.materials.git_diffs.models import GitDiffMaterialQuery

    from pytoy.tool_execution.execution_environment.manager import EnvironmentManager

    buffer = PytoyBuffer.get_current()
    if not buffer.is_file:
        raise ValueError("Target buffer is not file.")
    path = buffer.file_path if buffer.is_file else Path().cwd()
    workspace = EnvironmentManager().find_workspace(path, preference="system")
    workspace = workspace or path.parent

    collector = GitDiffCollector(path)
    query = GitDiffMaterialQuery()
    bundle = collector.get_material(query)
    composer = MaterialDataExplorerTaskComposer([bundle.text_material_data])
    section_text = composer.compose_system_prompt()
    buffer = make_buffer("__docs__", "vertical")
    buffer.init_buffer()
    buffer.append(section_text)


@app.command("ThreeWordStoryExperiment")
def three_word_story(user_prompt: Annotated[str | None, Option()] = None):
    from pytoy.tool_execution.execution_environment import EnvironmentManager
    from pytoy.tools.llm.stories.three_word_story import ThreeWordsStoryController

    manager = EnvironmentManager()
    workspace = manager.find_workspace(__file__)
    if workspace is None:
        raise ValueError("Apt folder is not found")
    folder = workspace / "mybag" / "ThreeWordStory"
    controller = ThreeWordsStoryController.from_any(folder)
    if user_prompt is None:
        line_range = PytoyWindow.get_current().selected_line_range
        lines = PytoyBuffer.get_current().get_lines(line_range)
        user_prompt = "\n".join(lines)
    controller.make_progress(user_prompt)
