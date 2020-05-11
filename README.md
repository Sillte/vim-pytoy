# vim-pytoy
Miscellaneous python operations around me. (Personal practice for vim-plugin.)

## My Rules

Policy of implementation, mainly for my personal memorandum.

### Calling python functions

#### Handling of the parameters.
```vim
function! Func(...)
py3 func()
endfunction
```

```python
def func():
    import vim
    args = vim.eval("a:000")
```

#### Handling of the return.
If `python` functions needs to return value,  
then `g:pytoy_return` is used as a return value.

```vim
function! Func()
py3 func()
return pytoy_:return
endfunction
```

```python
def func():
    ...
    import vim
    ret = 3
    vim.command(":let l:ret='{ret}'")
```
