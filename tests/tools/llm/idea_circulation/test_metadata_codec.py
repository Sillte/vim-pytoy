import yamlrocks
from pytoy_llm.models import LLMTokens

from pytoy.tools.llm.idea_circulation.metadata_codec import BufferMetadataCodec
from pytoy.tools.llm.idea_circulation.statuses import IdeaCirculationStatus


def test_metadata_codec_serializes_status() -> None:
    status = IdeaCirculationStatus(workspace_name="sample", value_cycle_working_status="working")
    status.update_tokens(LLMTokens(prompt=3, completion=4, total=7, cache_read=1, cache_write=2))

    patch = BufferMetadataCodec.from_any(status=status).create_patch("# Idea circulation\n")
    metadata = yamlrocks.loads("\n".join(patch.lines[1:-1]))

    assert metadata == {
        "kind": "idea-circulation",
        "workspace_name": "sample",
        "value_cycle_execution_policy": "enabled",
        "value_cycle_working_status": "working",
        "llm_tokens": {"prompt": 3, "completion": 4, "total": 7, "cache_read": 1, "cache_write": 2},
    }
