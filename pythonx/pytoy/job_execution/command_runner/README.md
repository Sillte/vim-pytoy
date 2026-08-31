# Design Policy

## Design

Job event callbacks belong to the backend's UI execution context. The relevant
context is not necessarily `threading.main_thread()`; Vim and Neovim may impose
their own event-loop or thread-affinity requirements.

Process workers must remain separate from that context. They may perform I/O and
transfer notifications, but must not access UI components or emit job events
directly. The backend dispatcher is responsible for serializing those
notifications before invoking callbacks that may access the UI.

## Discussions

The Dummy backend needs an application loop or dispatcher with the same properties. 