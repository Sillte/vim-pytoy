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

function! pytoy#stop()
python3 pytoy.stop()
endfunction

function! pytoy#is_running()
python3 pytoy.is_running()
return l:ret
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
return l:ret 
endfunction


" Mapping definition 
nnoremap \p :call pytoy#run()<CR>
nnoremap <expr><silent> <C-c> pytoy#is_running() ? pytoy#stop() : "\<C-c>"
