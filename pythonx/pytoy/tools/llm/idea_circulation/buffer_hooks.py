from pytoy_llm.idea import IdeaSpace

from pytoy.tool_session.llm import LLMSessionBufferHooks


def build_buffer_hooks(idea_space: IdeaSpace) -> LLMSessionBufferHooks:
    actions = dict()

    def on_creation(buffer):
        buffer.metadata.data["idea-space"] = idea_space

    return LLMSessionBufferHooks(actions=actions, on_creation=on_creation)
