# Development Tool Specifications

## `VimPluginPackage.restart()` cache artifacts

Restarting through `VimPluginPackage.restart()` on a supported editor backend
creates or overwrites both of these files in the active editor's cache folder:

- `pytoy_reboot.json`
- `pytoy_reboot.vim`

The JSON file contains the invocation time as `time` and the detected plugin
root as `plugin_folder`. The Vim session file is generated from the current
editor session and can be sourced by Vimscript configuration.

The cache folder is the editor-provided `stdpath('cache')` for Neovim and the
VS Code Neovim backend. For Vim, it is `$XDG_CACHE_HOME/vim` when
`XDG_CACHE_HOME` is set, otherwise `~/.cache/vim`.
