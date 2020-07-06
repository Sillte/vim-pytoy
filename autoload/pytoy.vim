"Related to initialization.
function! pytoy#init_python()
" Solve the `import` libraries.
" Assume that `library` exists in `pythonx` folder.
python3 << EOF
import sys, os, vim
plugin_folder = os.path.dirname(vim.eval("expand('<sfile>:p:h')"))
library_folder = os.path.join(plugin_folder, "pythonx")
if library_folder not in sys.path: 
    sys.path.append(library_folder)
try:
    import pytoy
except Exception as e:
    print("Failed to Import.", e)
    raise e
else:
    vim.command("let s:init_python=1")
EOF
endfunction

function! pytoy#reset_python()
python3 pytoy.reset_python()
endfunction

if !exists("s:init_python") || (s:init_python != 1)
    call pytoy#init_python()
else
    call pytoy#reset_python()
    call pytoy#init_python()
endif 

" Python Execution.

function! pytoy#run()
python3 pytoy.run()
endfunction

function! pytoy#rerun()
python3 pytoy.rerun()
endfunction

function! pytoy#stop()
python3 pytoy.stop()
endfunction

function! pytoy#is_running()
python3 pytoy.is_running()
return g:pytoy_return
endfunction

function! pytoy#reset()
python3 pytoy.reset()
endfunction

" Virual Environment handling.
function! pytoy#activate(...)
python3 pytoy.activate()
endfunction

function! pytoy#deactivate()
python3 pytoy.deactivate()
endfunction

function! pytoy#envinfo()
python3 pytoy.envinfo()
return g:pytoy_return
endfunction


" Related to python module handling (jedi)
function! pytoy#goto()
python3 pytoy.goto()
endfunction


" Mapping definition 
nnoremap \p :call pytoy#run()<CR>
nnoremap \P :call pytoy#rerun()<CR>
nnoremap <expr><silent> <C-c> pytoy#is_running() ? pytoy#stop() : "\<C-c>"

" For pytoy#goto, Vim8.2+ is required.
if 802 <= v:version 
    " To solve collision with `jedi's original (recommended) key mapping.
    let g:jedi#goto_command="_\\d"
    nnoremap \d :call pytoy#goto()<CR>
endif 
