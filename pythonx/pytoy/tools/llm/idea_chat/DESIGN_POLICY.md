# Design Policy

## Purpose

`idea_chat` provides a session-backed conversational interface with an
`IdeaSpace`. It connects a user-facing chat buffer to LLM execution while
modifying and preserving the conversation document in the buffer and `IdeaSpace`.

## Terminology

- `IdeaChatHandler`: the public entry point used to create or access an Idea
  chat session.
- `IdeaChatDriver`: the session implementation that coordinates task creation,
  buffer updates, and IdeaSpace preparation.


## Responsibility Boundaries

`IdeaChatHandler` owns session discovery and creation. It exposes the small
operation surface needed by commands and other package consumers.

`IdeaChatDriver` owns the session workflow:

- reading and updating the chat buffer;
- constructing LLM task specifications;
- preparing the IdeaSpace directory;
- applying successful conversation history;
- reporting execution failures to the chat buffer.

The codecs own only conversion between the chat buffer representation and LLM
messages. They do not create sessions, execute tasks, or mutate buffers.

`BufferMetaDataCodec` separately converts the buffer front-matter. It stores
only `title`; a missing dashboard title is represented as YAML `null` in the
buffer. 

The LLM execution and session packages own asynchronous execution and session
lifecycle. `idea_chat` consumes those contracts and does not reimplement them.

Standard LLM execution lifecycle events are recorded by the common LLM logger.
IdeaChat may additionally record buffer and codec details in its feature-level
diagnostic logger. Those details are not a replacement for the common
lifecycle records.

## Public API

Consumers import `IdeaChatHandler` from `pytoy.tools.llm.idea_chat`.

The following modules and symbols are implementation details:

- `driver.py` and `IdeaChatDriver`;
- `handler.py`;
- `buffer_codec.py` and its codec types;
- `messages_codec.py` and its codec types;
- `prompts.py` and prompt constants.

They must not be imported by package consumers merely for convenience. If a
concept becomes a stable extension contract, it should be deliberately added
to `idea_chat.__init__` and documented here.

## Rules

- A chat session is identified by the package-owned session kind and buffer
  name, together with its `idea_space` and `workspace` metadata.
- Existing sessions are reused only when their identifying metadata matches.
- Creating an IdeaChat session while another session of the same kind has
  different identifying metadata is an error.
- Conversation history is stored only in the marked message domain; ordinary
  buffer content remains outside the codec's replacement range.
- System messages may be used to construct an LLM request but are not written
  to the user-editable conversation history format.
- Execution failures are represented in the session execution outcome and are
  appended to the chat buffer by the driver.


