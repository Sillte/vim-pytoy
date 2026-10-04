from pathlib import Path

import yamlrocks
from pytoy_llm.models import LLMParam, LLMTokens, UsageLimit

from pytoy.tools.llm.idea_chat.metadata_codec import BufferMetadataCodec


def test_dashboard_title_is_read_from_idea_note_metadata(tmp_path: Path):
    dashboard = tmp_path / "dashboard.md"
    dashboard.write_text('---\ntitle: "設計相談"\n---\n\n# Dashboard\n')

    assert BufferMetadataCodec.from_dashboard(dashboard, kind="idea-chat").title == "設計相談"


def test_missing_dashboard_title_is_written_as_yaml_null():
    patch = BufferMetadataCodec().create_patch("# Dashboard\n")

    assert patch.lines == [
        "---",
        "title:",
        "kind: idea-chat",
        "---",
    ]


def test_token_usage_is_written_to_front_matter():
    tokens = LLMTokens(prompt=12, completion=4, total=16)

    patch = BufferMetadataCodec(llm_tokens=tokens).create_patch("# Dashboard\n")

    assert patch.lines == [
        "---",
        "title:",
        "kind: idea-chat",
        "llm_tokens:",
        "  prompt: 12",
        "  completion: 4",
        "  total: 16",
        "---",
    ]


def test_dashboard_title_patch_replaces_only_front_matter():
    content = "---\ntitle: null\n---\n\n---LLMMessages-BEGIN---\nconversation\n---LLMMessages-END---\n"

    patch = BufferMetadataCodec(title="New title").create_patch(content)

    assert patch.line_range.start == 0
    assert patch.line_range.end == 3
    assert patch.lines == [
        "---",
        "title: New title",
        "kind: idea-chat",
        "---",
    ]


def test_dashboard_title_patch_preserves_leading_blank_lines():
    content = "\n\n---\ntitle: null\n---\nconversation\n"

    patch = BufferMetadataCodec(title="New title").create_patch(content)

    assert patch.line_range.start == 2
    assert patch.line_range.end == 5
    assert patch.lines == [
        "---",
        "title: New title",
        "kind: idea-chat",
        "---",
    ]


def test_detail_metadata_includes_llm_configuration():
    codec = BufferMetadataCodec(
        llm_param=LLMParam(temperature=0.4),
        usage_limit=UsageLimit(max_requests=5),
        connection_name="local",
    )

    patch = codec.create_patch("# Dashboard\n")
    front_matter = yamlrocks.loads("\n".join(patch.lines[1:-1]))
    assert isinstance(front_matter, dict)

    assert front_matter["llm_param"] == {"temperature": 0.4}
    assert front_matter["usage_limit"] == {"max_requests": 5}
    assert front_matter["connection_name"] == "local"


def test_summary_metadata_removes_existing_token_usage():
    content = (
        "---\n"
        "title: null\n"
        "kind: idea-chat\n"
        "llm_tokens:\n"
        "  prompt: 12\n"
        "  completion: 4\n"
        "  total: 16\n"
        "---\n"
        "conversation\n"
    )

    patch = BufferMetadataCodec().create_patch(content)

    assert patch.line_range.start == 0
    assert patch.line_range.end == 8
    assert patch.lines == ["---", "title:", "kind: idea-chat", "---"]
