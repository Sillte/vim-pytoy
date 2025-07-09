"""This works only when `vscode+nvim`
"""

from pathlib import Path 
from pydantic import BaseModel,ConfigDict

class Api:
    def __init__(self):
        import vim
        vim.exec_lua("_G.vscode_api_global = require('vscode')")
        self._api = vim.lua.vscode_api_global
        
    def eval_with_return(self, js_code: str,
                         args: None | dict = None,  
                         with_await: bool=True):
        """Evaluate `js_code` with `args`. 
        Example:
            api.eval_with_return("vscode.window.activeTextEditor.document.fileName",
                               with_await=False)

        """
        if not args:
            args = dict()
        if not with_await:
            ret = self._api.eval(f"return {js_code}", args)
        else:
            ret = self._api.eval(f"return await {js_code}", args)
        return ret
    
    def action(self, name, opts=None): 
        # For `opts`, See.
        # https://github.com/vscode-neovim/vscode-neovim/tree/master?tab=readme-ov-file#vscodeactionname-opts
        if opts is None:
            opts = {}
        return self._api.action(name, opts)

    def call(self, name, opts=None, timeout=-1):
        # https://github.com/vscode-neovim/vscode-neovim/tree/master?tab=readme-ov-file#vscodecallname-opts-timeout
        if opts is None:
            opts = {}
        return self._api.call(name, opts, timeout)
    
