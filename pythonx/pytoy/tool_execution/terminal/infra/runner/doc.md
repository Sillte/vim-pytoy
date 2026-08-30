"""
Compatibility Matrix for Ctrl+C (SIGINT) in Windows Environments:

| Control Method / Env      | VIM (term) | VIM (winpty) | NVIM (job) | NVIM+VSCode(job) | NVIM+VSCode(winpty) |
|:--------------------------|:----------:|:------------:|:----------:|:----------------:|:-------------------:|
| GenerateConsoleCtrlEvent  | OK (Note 1)| OK (Reliable)| OK         | NG (Isolated)    | NG (Isolated)       |
| send("\\x03") directly    | OK (Note 3)| OK? (Note 2) | OK         | NG (Filtered)    | NG (Filtered)       |
| PTY Layer                 | ConPTY     | winpty-agent | ConPTY     | Headless / RPC   | Headless / RPC      |
| Process Group Ownership   | Vim        | Python       | Neovim     | Nvim (Embedded)  | Python (Direct)     |

[Crucial Observations]
- Note 1 (VIM term): Works because Vim owns a visible Win32 Console window.
- Note 2 (winpty): winpty often captures \x03 as a literal character rather than 
  a break signal unless the terminal state is perfectly 'raw', which is 
  difficult to maintain across different shell environments (IPython, etc.).
- Note 3 (VIM term): Works because `:term` handles the PTY bridge correctly.

[The VSCode Extension "Headless" Problem]
In VSCode + Neovim Extension, the 'Headless' nature of the embedded Neovim 
means no Win32 Console Session is allocated. Even if Python spawns its own 
winpty, the lack of an interactive console session for the parent process 
prevents 'GenerateConsoleCtrlEvent' from being authorized by the OS kernel.
"""
