"""This works only when `vscode+nvim`"""

from typing import Mapping, Any


class Api:
    def __init__(self):
        import vim

        vim.exec_lua("_G.vscode_api_global = require('vscode')")  # type: ignore[attr-defined]
        self._api = vim.lua.vscode_api_global # type: ignore[attr-defined]

    def eval_with_return(
        self, js_code: str, opts: None | Mapping[str, Any] = None, with_await: bool = True
    ):
        """Evaluate `js_code` with `opts`.
        Example:
            api.eval_with_return("vscode.window.activeTextEditor.document.fileName", with_await=False)
        """
        if opts is None:
            opts = dict()
        if not with_await:
            ret = self._api.eval(f"return {js_code}", opts)
        else:
            ret = self._api.eval(f"return await {js_code}", opts)
        return ret

    def action(self, name: str, opts: Mapping[str, Any] | None = None) -> Any:
        # For `opts`, See.
        # https://github.com/vscode-neovim/vscode-neovim/tree/master?tab=readme-ov-file#vscodeactionname-opts
        if opts is None:
            opts = {}
        return self._api.action(name, opts)

    def call(self, name: str, opts: Mapping[str, Any] | None = None, *, timeout=-1) -> Any:
        # https://github.com/vscode-neovim/vscode-neovim/tree/master?tab=readme-ov-file#vscodecallname-opts-timeout
        if opts is None:
            opts = {}
        return self._api.call(name, opts, timeout)
