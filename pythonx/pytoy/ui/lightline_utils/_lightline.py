import vim

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
        # 辞書のキーの共通部分を取得
        common_keys = set(arg.keys()) & set(self.data.keys())
        for key in common_keys:
            self.data[key] = arg[key]
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
        if int(vim.eval("exists('lightline#init')")):
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