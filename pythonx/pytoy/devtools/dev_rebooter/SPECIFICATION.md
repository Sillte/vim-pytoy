# Development Tool Specifications

## `PluginRebooter.restart()` cache artifacts

`PluginRebooter.restart()` prepares a `RebootInfo`, writes its metadata and
(for editor backends) the current editor session to cache files, then asks the
active backend to restart. The cache files are created or overwritten:

- `pytoy_reboot.json`
- `pytoy_reboot.vim`

The cache folder is selected by the backend:

- Vim: `$XDG_CACHE_HOME/vim` when `XDG_CACHE_HOME` is set, otherwise
  `~/.cache/vim`.
- Neovim and VS Code Neovim: the editor-provided `stdpath('cache')`.
- Dummy backend: `$XDG_CACHE_HOME/dummy_pytoy` when `XDG_CACHE_HOME` is set,
  otherwise `~/.cache/dummy_pytoy`.

The selected directory is created if it does not exist.

### `RebootInfo`

`RebootInfo` is the in-memory handoff between a backend rebooter's `prepare()`
and `reboot(info)` operations. Its fields are:

| Field | Type | Meaning |
| --- | --- | --- |
| `session_file` | `Path` | Path to `pytoy_reboot.vim`. |
| `metafile_path` | `Path` | Path to `pytoy_reboot.json`. |
| `plugin_root_folder` | `Path` | Root detected for the Python/UV project containing the plugin. |
| `debug_venv_path` | `Path \| None` | Virtual-environment path found for that workspace, or `None` when no path is found. |

`RebootInfo` is frozen after creation. Its `dump()` method writes the metadata
JSON; it does not serialize the dataclass fields wholesale.

### JSON metadata format

`pytoy_reboot.json` is a JSON object with these keys:

| Key | JSON type | Meaning |
| --- | --- | --- |
| `time` | number | Unix timestamp (seconds) when `dump()` ran. |
| `plugin_folder` | string | `plugin_root_folder` in POSIX path form. |
| `debug_venv_path` | string or `null` | `debug_venv_path` in POSIX path form, or `null` if it is `None`. |

`session_file` and `metafile_path` are intentionally not duplicated in the
JSON: their names and locations are determined by the cache directory and the
fixed cache filenames above. Consumers that need the debug environment can
read `debug_venv_path`; they must handle `null` as “no environment was found.”

### Session and restart behavior

For Vim, Neovim, and VS Code Neovim, `prepare()` adds `plugin_root_folder` to
the current editor's `runtimepath`, then writes the current session to
`pytoy_reboot.vim` using `mksession!`. `dump()` writes `pytoy_reboot.json`
after preparation and before the backend restarts. The session file contains
editor session state; it is separate from the reboot metadata and is not the
serialization format for `RebootInfo`. The Dummy backend writes the JSON
metadata but does not create an editor session or restart an editor.

For standalone Vim and Neovim, a non-minimal restart passes
`g:pytoy_reboot` and, when available, `g:pytoy_debug_venv` as startup commands.
These globals are not stored by `mksession`; the metadata JSON is the
persistent handoff for values that Vimscript configuration needs to read.
Minimal restart omits these restart globals. VS Code Neovim requests the
`vscode-neovim.restart` action instead of starting another editor process.
