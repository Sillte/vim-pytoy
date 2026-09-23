from pathlib import Path

from pytoy.tools.llm.idea_chat.metadata_codec import BufferMetadataCodec


def test_dashboard_title_is_read_from_idea_note_metadata(tmp_path: Path):
    dashboard = tmp_path / "dashboard.md"
    dashboard.write_text('---\ntitle: "設計相談"\n---\n\n# Dashboard\n')

    assert BufferMetadataCodec.from_dashboard(dashboard, kind="idea-chat").title == "設計相談"


def test_missing_dashboard_title_is_written_as_yaml_null():
    patch = BufferMetadataCodec().create_patch("# Dashboard\n")

    assert patch.lines == ["---", "title:", "kind: idea-chat", "---"]


def test_dashboard_title_patch_replaces_only_front_matter():
    content = "---\ntitle: null\n---\n\n---LLMMessages-BEGIN---\nconversation\n---LLMMessages-END---\n"

    patch = BufferMetadataCodec(title="New title").create_patch(content)

    assert patch.line_range.start == 0
    assert patch.line_range.end == 3
    assert patch.lines == ["---", "title: New title", "kind: idea-chat", "---"]


def test_dashboard_title_patch_preserves_leading_blank_lines():
    content = "\n\n---\ntitle: null\n---\nconversation\n"

    patch = BufferMetadataCodec(title="New title").create_patch(content)

    assert patch.line_range.start == 2
    assert patch.line_range.end == 5
    assert patch.lines == ["---", "title: New title", "kind: idea-chat", "---"]
