# vim-pytoy 

A Python-powered plugin framework for Vim/Neovim/VSCode,
designed to run and integrate developer tools directly inside editor buffers.
This project is not intended for public release.
For now, it serves as a personal practice project for Vim plugin development.

## Example of command.

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

2. Execute the python script or vim source

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
    - ```json
    {
     "vscode-neovim.useWSL": true, 
     "vscode-neovim.neovimExecutablePaths.linux": "/home/zaube/.local/bin/nvim",
    }
      ```
* For specific dependecy, please refer to [pyproject.toml](pyproject.toml)

## Design Overview

**vim-pytoy** is a Python utility framework that integrates with Vim/Neovim and VSCode, enabling users to leverage Python tools and scripts within their editor. 

### Architecture: Layered Design

The framework follows a **3-layer architecture**:

1. **Commands Layer**: Vim `:Commands` exposed to users (`:Pytest`, `:RuffCheck`, etc.)
2. **Tools Layer**: High-level integrations (Python executor, pytest runner, Git tools, LLM integration)  
3. **Shared Infrastructure**: Core abstractions (Command framework, UI system, timers, config, logging)

```
Commands (:PytoyPytest, :PytoyGit, etc.)
    ↓
Tools (pytest, git, llm, python, cspell)
    ↓
Shared Infrastructure (command, ui, timertask, config)
```

### Detailed Module Reference

#### **shared/command/** - Command Framework
- Declarative Vim `:Command` definition using Python decorators
- Key exports: `CommandApplication`, `CommandGroup`, `Argument`, `Option`, `Field`
- Supports Vim ranges (`RangeParam`), counts (`CountParam`), and hierarchical grouping

#### **shared/ui/** - Unified UI Interface
Cross-platform abstraction providing consistent APIs across all editors:

- **`pytoy_buffer`**: Text buffer/document abstraction
  - Unified read/write/manipulation API

- **`pytoy_window`**: Editor window/editor abstraction
  - Window navigation, splitting, layout management

- **`pytoy_quickfix`**: Error list abstraction  
  - `QuickfixRecord`: Unified error/warning representation
  - `handle_records()`: Display errors across editors

- **`notifications`**: Cross-platform message display

- **`status_line`**: Status bar integration  

- **`vscode/`**: VSCode-specific implementations

#### **shared/timertask/** - Asynchronous Callbacks
- Python functions as Vim timer callbacks (integrates with `timer_start`, `timer_stop`)
- Non-blocking editor integration

#### **shared/pytoy_configuration/** - Configuration Management
- Setting persistence and retrieval of configurations

#### **shared/loggers/** - Logging System
- Unified logging across components
- Production and debug levels

#### **job_execution/command_executor/** - Command Coordination
- `CommandExecutionManager` singleton: Track and coordinate running commands
- Non-blocking execution via event loop

#### **job_execution/terminal_executor/** - Terminal Management  
- `TerminalExecutionManager`: Manage interactive terminal sessions
- Multi-driver architecture:
  - `impl_win.py`: Windows console driver
  - `impl_unix.py`: Unix/TTY driver  
  - Pluggable driver system

#### **job_execution/environment_manager/** - Environment Isolation
- Virtual environment management (uv)

#### **job_execution/[command|terminal]_runner/** - Execution Primitives
- Low-level command/process execution
- Output stream capture and forwarding

#### **tools/python/** - Python Script Execution
- `PythonExecutor`: Execute `.py` files with isolated STDOUT/STDERR
- Integration with buffer output system

#### **tools/pytest/** - Test Framework Integration
- Test discovery and execution
- Result parsing and quickfix display

#### **tools/git/** - Git Integration
- Git related opeations


#### **commands/** - User-Facing Commands
Vim command definitions that compose tools and infrastructure:

- `console_command.py`: Interactive console (REPL)
- `env_commands.py`: Virtual environment management
- `git_commands.py`: Git operations
- `llm_commands.py`: AI-assisted coding  
- `pytools_commands.py`: Python tools (pytest, execution, etc.)
- `devtools_commands.py`: Development utilities
- `vscode_commands/`: VSCode-specific adapters

#### **contexts/[core|vim|vscode|pytoy]/** - Global State
Singleton pattern for cross-module coordination:

- `GlobalPytoyContext`: Main entry point
  - `command_execution_manager`: Running commands
  - `terminal_execution_manager`: Active terminals
  - `terminal_driver_manager`: Terminal driver allocation
  - `fairy_kernel_manager`: LLM kernels

- Environment-specific contexts for Vim, Neovim, VSCode

#### **devtools/** - Development Support
- `vim_rebooter`: Plugin reload for development
- `vimplugin_package`: Plugin packaging utilities

### Design Patterns

- **Singleton**: Global context managers ensure single instance coordination
- **Decorator**: Commands defined via `@app.command()` decorators
- **Lazy Loading**: Components initialized on-demand for startup performance

### Comments

This project is primarily a personal exploration,
but it aims to experiment with structured plugin design.

