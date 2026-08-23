from pytoy.shared.command import App
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer import make_buffer


app = App()


@app.command("GatherTextFiles")
def gather_text_files():
    from pytoy_llm.materials.text_files import TextFilesCollector, TextFilesMaterialQuery
    from pytoy_llm.composers.materials import MaterialDataExplorerTaskComposer
    from pytoy.job_execution.environment_manager import EnvironmentManager

    buffer = PytoyBuffer.get_current()
    if not buffer.is_file:
        raise ValueError("Target buffer is not file.")
    path = buffer.file_path
    workspace = EnvironmentManager().find_workspace(path, preference="system")
    workspace = workspace or path.parent
    query = TextFilesMaterialQuery.from_any(collection_root=path, patterns=[""], max_depth=None)
    material = TextFilesCollector(workspace=workspace).get_material(query)
    composer = MaterialDataExplorerTaskComposer([material.text_material_data])
    section_text = composer.compose_system_prompt()
    buffer = make_buffer("__docs__", "vertical")
    buffer.init_buffer()
    buffer.append(section_text)


@app.command("GatherGitDiffs")
def gather_git_diffs():
    from pytoy_llm.materials.git_diffs.collectors import GitDiffCollector
    from pytoy_llm.materials.git_diffs.models import GitDiffMaterialQuery
    from pytoy_llm.composers.materials import MaterialDataExplorerTaskComposer
    from pytoy.job_execution.environment_manager import EnvironmentManager
    from pathlib import Path

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