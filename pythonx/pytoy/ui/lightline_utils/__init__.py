"""Personal utility functions for using `lightline`.

This module assumes the following plugin is already installed. 
* https://github.com/itchyny/lightline.vim

Policy
------

Note
----------------
This is an inefficient wrapper, yet.


Copyright of `lightline`.:

* https://github.com/itchyny/lightline.vim
* Copyright: Copyright (c) 2013-2020 itchyny

Thank you for the great plugin! 
"""

import vim

class _Lightline:
    """ This class is intended to be a wrapper for `g:lightline`.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, arg=None, **kwargs):
        if getattr(self, '_initialized', False):
            return

        if arg is None:
            arg = dict()
        self.data = _G_LIGHTLINE
        arg.update(kwargs)
        for key in (arg & self.data.keys()):
            self.data[key] = arg
        self.init()
        self._initialized = True

    def _sync(self):
        """Synchronize `self.data` with `g:lightline`.
        """
        d = vim.eval("g:lightline")
        d.update(self.data)
        self.data = d
        vim.command(f"let g:lightline={self.data}")

    def __setitem__(self, key, value):
        # This is insufficient, since `self["active"]["invalid"] = "hoge"` is accepted.
        if key not in self.data:
            raise ValueError(f"Invalid key. `{key}`")
        self.data[key] = value
        
    def __getitem__(self, key):
        return self.data[key]

    def init(self): 
        # Here, synchronize `self.data` and `g:lightline`. 
        self._sync()
        vim.command("call lightline#init()")

    def mode(self): 
        return vim.eval("lightline#mode()")

    def enable(self): 
        self._sync()
        vim.command("call lightline#enable()")

    def disable(self): 
        self._sync()
        vim.command("call lightline#disable()")

    def toggle(self): 
        self._sync()
        vim.command("call lightline#toggle()")

    def link(self, mode): 
        vim.command(f"call lightline#link('{mode}')")

    def highlight(self): 
        vim.command(f"call lightline#highlight()")

    def statusline(self, inactive=0): 
        return vim.eval(f"lightline#statusline({inactive})")

    def tabline(self): 
        return vim.eval(f"lightline#tabline()")

    def concatenate(self, list, num=0): 
        return vim.eval(f"lightline#concatenate({list}, {num})")

    def palette(self): 
        return vim.eval(f"lightline#palette()")

    def colorscheme(self): 
        vim.command(f"let g:lightline={self.data}")
        ret = vim.command("call lightline#colorscheme()")

    def update(self): 
        self._sync()
        vim.command("call lightline#update()")

# Ref: https://github.com/itchyny/lightline.vim/blob/master/autoload/lightline.vim
# Commit: 893bd90787abfec52a2543074e444fc6a9e0cf78
# Github: https://github.com/itchyny/lightline.vim
# Copyright: Copyright (c) 2013-2020 itchyny
vim.command(r"""let g:_lightline={
      \   'active': {
      \     'left': [['mode', 'paste'], ['readonly', 'filename', 'modified']],
      \     'right': [['lineinfo'], ['percent'], ['fileformat', 'fileencoding', 'filetype']]
      \   },
      \   'inactive': {
      \     'left': [['filename']],
      \     'right': [['lineinfo'], ['percent']]
      \   },
      \   'tabline': {
      \     'left': [['tabs']],
      \     'right': [['close']]
      \   },
      \   'tab': {
      \     'active': ['tabnum', 'filename', 'modified'],
      \     'inactive': ['tabnum', 'filename', 'modified']
      \   },
      \   'component': {
      \     'mode': '%{lightline#mode()}',
      \     'absolutepath': '%F', 'relativepath': '%f', 'filename': '%t', 'modified': '%M', 'bufnum': '%n',
      \     'paste': '%{&paste?"PASTE":""}', 'readonly': '%R', 'charvalue': '%b', 'charvaluehex': '%B',
      \     'spell': '%{&spell?&spelllang:""}', 'fileencoding': '%{&fenc!=#""?&fenc:&enc}', 'fileformat': '%{&ff}',
      \     'filetype': '%{&ft!=#""?&ft:"no ft"}', 'percent': '%3p%%', 'percentwin': '%P',
      \     'lineinfo': '%3l:%-2v', 'line': '%l', 'column': '%c', 'close': '%999X X ', 'winnr': '%{winnr()}'
      \   },
      \   'component_visible_condition': {
      \     'modified': '&modified||!&modifiable', 'readonly': '&readonly', 'paste': '&paste', 'spell': '&spell'
      \   },
      \   'component_function': {},
      \   'component_function_visible_condition': {},
      \   'component_expand': {
      \     'tabs': 'lightline#tabs'
      \   },
      \   'component_type': {
      \     'tabs': 'tabsel', 'close': 'raw'
      \   },
      \   'component_raw': {},
      \   'tab_component': {},
      \   'tab_component_function': {
      \     'filename': 'lightline#tab#filename', 'modified': 'lightline#tab#modified',
      \     'readonly': 'lightline#tab#readonly', 'tabnum': 'lightline#tab#tabnum'
      \   },
      \   'colorscheme': 'default',
      \   'mode_map': {
      \     'n': 'NORMAL', 'i': 'INSERT', 'R': 'REPLACE', 'v': 'VISUAL', 'V': 'V-LINE', "\<C-v>": 'V-BLOCK',
      \     'c': 'COMMAND', 's': 'SELECT', 'S': 'S-LINE', "\<C-s>": 'S-BLOCK', 't': 'TERMINAL'
      \   },
      \   'separator': { 'left': '', 'right': '' },
      \   'subseparator': { 'left': '|', 'right': '|' },
      \   'tabline_separator': {},
      \   'tabline_subseparator': {},
      \   'enable': { 'statusline': 1, 'tabline': 1 },
      \   '_mode_': {
      \     'n': 'normal', 'i': 'insert', 'R': 'replace', 'v': 'visual', 'V': 'visual', "\<C-v>": 'visual',
      \     'c': 'command', 's': 'select', 'S': 'select', "\<C-s>": 'select', 't': 'terminal'
      \   },
      \   'mode_fallback': { 'replace': 'insert', 'terminal': 'insert', 'select': 'visual' },
      \   'palette': {},
      \   'winwidth': winwidth(0),
      \ }
""".replace("\n", " ").replace("\\", " "))
# 
# If `g:lightline` is not defined, then default value is used.

vim.command("""
if !exists("g:lightline")
    let g:lightline = g:_lightline
endif
""")

_G_LIGHTLINE = vim.eval("g:lightline")


"""
Below, customization.
"""

from pytoy.infra.vim_function import PytoyVimFunctions

class Lightline(_Lightline):
    """

    Args:
        initialize(bool): If `True`, `g:lightline` returns to `default` of this module. 

    Note
    ------
    (2020-05-10) Currently, this is not far from good state.
    """

    _infos = dict()

    def default(self):
        """To my default state.
        """
        self.data = vim.eval("g:_lightline")
        self.enable()
        return self.data

    def _to_funcname(self, func):
        if callable(func):
            vimfunc_name = PytoyVimFunctions.register(func)
            vim.command(f"echo exists('{vimfunc_name}')")
            vim.command(f"echo exists('g:lightline')")
        else:
            vimfunc_name = func
        return vimfunc_name


    def register(self, func, mode="active", direction="left", level=-1, index=None, name=None):
        """Register `func`. 

        Args:
            func (str or function): the target funciton.
            mode(str): "active" or "inactive"
            direction(str): "left" or "right"
            level(int): the index of `self[{mode}][{direction}]`, which represents the group
            index(int, None): If non-negative interger is specified, then inserted to `self[{mode}][{direction}][{index}]`.

        Return (str):
            key of registration, which equals to `vim-function` name.

        Note
        ----------------------------------------------------------------------------
        It is intended that `self` is regarded as ``g:lightline``.
        """
        assert mode in {"active", "inactive"}
        assert direction in {"left", "right"}

        key = self._to_funcname(func)

        if key in self._infos:
            self.deregister(key)

        if name is None:
            name = key

        targets = self[mode][direction]
        n_level = len(targets)
        if 0 <= level < n_level:
            if index is None:
                targets[level].append(name)
            else:
                targets[level].insert(index, name)
        else:
            targets.append([name])

        # Register about `component`.
        if PytoyVimFunctions.is_registered(key):
            c_type = "component_function"
        else:
            c_type = "component"
        self[c_type][name] = key

        info = dict()
        info["name"] = name
        info["key"] = key
        info["component_type"] = c_type
        self._infos[key] = info

        self.update()
        self.enable()

        return key

    def deregister(self, key, strict_error=False):
        """Deregister function.

        Args:
            key (str, function): key of registration, which is the same as vim-function name.
            strict_error(bool): If `True` and `key` is not existent, raise `ValueError`.

        Raise:
            ValueError:
        
        """
        key = self._to_funcname(key)
        if key not in self._infos:
            if strict_error:
                raise ValueError(f"`{key}` is not existent.")
            else:
                return 

        # Deregister about `name`.
        info = self._infos[key]
        name = info["name"]
        for mode in ("active", "inactive"):
            for direction in ("left", "right"):
                self[mode][direction] = [ [elem for elem in sub if elem != name] for sub in self[mode][direction]]

        # Deregister about `component` / `component_function`.
        # Register about `component`.
        if PytoyVimFunctions.is_registered(key):
            c_type = "component_function"
        else:
            c_type = "component"
        del self[c_type][name]
        #print("self[c_type]", self[c_type])

        # Deletion of `key`. 
        del self._infos[key]

        self.update()
        self.enable()

    def is_registered(self, key):
        key = self._to_funcname(key)
        return key in self._infos
