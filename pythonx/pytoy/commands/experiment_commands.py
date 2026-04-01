from pytoy.shared.command import App
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer import make_buffer


app = App()


@app.command("GatherTextFiles")
def gather_text_files():
    from pytoy_llm.materials.text_files import TextFilesCollector
    from pytoy_llm.materials.composers import NaiveSectionComposer
    from pytoy.job_execution.environment_manager import EnvironmentManager

    buffer = PytoyBuffer.get_current()
    if not buffer.is_file:
        raise ValueError("Target buffer is not file.")
    path = buffer.path
    workspace = EnvironmentManager().get_workspace(path, preference="system")
    workspace = workspace or path.parent
    collector = TextFilesCollector(path, workspace=workspace)
    bundle = collector.bundle
    composer = NaiveSectionComposer([bundle.text_section_data])
    section_text = composer.compose_prompt()
    buffer = make_buffer("__docs__", "vertical")
    buffer.init_buffer()
    buffer.append(section_text)


@app.command("GatherGitDiffs")
def gather_git_diffs():
    from pytoy_llm.materials.git_diffs.collectors import GitDiffCollector
    from pytoy_llm.materials.git_diffs.models import GitDiffBundleQuery
    from pytoy_llm.materials.composers import NaiveSectionComposer
    from pytoy.job_execution.environment_manager import EnvironmentManager

    buffer = PytoyBuffer.get_current()
    if not buffer.is_file:
        raise ValueError("Target buffer is not file.")
    path = buffer.path
    workspace = EnvironmentManager().get_workspace(path, preference="system")
    workspace = workspace or path.parent

    collector = GitDiffCollector(path)
    query = GitDiffBundleQuery()
    bundle = collector.get_bundle(query)
    composer = NaiveSectionComposer([bundle.model_section_data])
    section_text = composer.compose_prompt()
    buffer = make_buffer("__docs__", "vertical")
    buffer.init_buffer()
    buffer.append(section_text)
