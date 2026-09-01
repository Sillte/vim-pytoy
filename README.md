# vim-pytoy

A Python-powered plugin framework for Vim/Neovim/VSCode,
designed to run and integrate developer tools directly inside editor buffers.

This project is currently a personal project rather than a public release.
For now, it focuses on exploring Vim plugin development and software architecture.

## Concept

This project follows the following principles:

* Python is the main programming language.
    * Application code does not use `VimScript`, `Lua`, or `TypeScript`.
* Most functionality is available across Vim/Neovim/VSCode using the same codebase.
    * The same codebase works, almost in the same way, across these environments.

These principles aim to provide high interoperability and ease of development
for plugin authors.

As a trade-off, platform-specific functionality and user experience are not
always given the highest priority.

## Example of command

1. Create a file for commands.

```python
from typing import Literal, Annotated
from pytoy.shared.command import App, Argument

app = App()


@app.command("Greeting")
def hello(arg: Annotated[Literal["morning", "evening"] | None, Argument()] = None):
    greeting = arg or "hello"
    print(f"{greeting.title()} from Pytoy!")
```

2. Save the script and execute the python script from the current buffer

```vim-command
:PytoyExecute
```

3. Execute the command.
```
:Greeting morning
```


## Environment

* Vim9.1+ 
* uv
* python3.13+

* psutil / pydantic / pywinpty
    - `python` is available for the environment these libraries should be installed (VIM). 
    - In the specified python environment, these libraries should be available (NVIM).  

* vscode + neovim extension 
    - [VSCode](https://code.visualstudio.com/)
    - [VSCode+neovim](https://github.com/vscode-neovim/vscode-neovim)
    - When you would like to use `WSL`, the following settings are necessary.
      ```json
      {
       "vscode-neovim.useWSL": true, 
       "vscode-neovim.neovimExecutablePaths.linux": "<Path to `neovim`>"
      }
      ```
* For specific dependency, please refer to [pyproject.toml](./pyproject.toml)

## Design Overview

Pytoy is organized into two broad areas:

- **Application**: Commands and Tools that provide user-facing functionality.
- **Library**: ToolExecution and Shared components that provide reusable execution
  and editor-integration infrastructure.

The main dependency direction is:

```text
Commands
    ↓
Tools
    ↓
ToolExecution
    ↓
Shared
```

### Application
#### Commands

User-facing commands exposed through Vim/Neovim.

Commands compose tools and invoke the functionality provided by the
lower-level library.

#### Tools

High-level integrations with developer tools such as Python, pytest, Git,
and other external tools.

Tools describe what Pytoy provides to users, while the lower layers
provide how those operations are executed.

### Library

#### Tool Execution

Infrastructure for executing external tools and managing their execution lifecycle.

The primary public API is the Handler, which represents a single execution
from the perspective of its consumer.

A typical execution follows this model:

```text
Request
   ↓
Handler
   ↓
Events / Results
```

Consumers should depend on public handlers and contract types rather
than on internal implementations.


Currently, the following types of executions are handled:

* command: execution of one command, such as `echo "hello, world"`.
* terminal: execution of the interactive command such as `ipython`.
* llm: execution of the one invocation of LLM. 


#### Shared

Common infrastructure used by the library and application layers.

This includes facilities such as:

* editor UI abstractions
* editor thread abstraction


