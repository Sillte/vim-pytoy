if &cp || exists("g:pytoy_loaded")
    finish
endif
let g:pytoy_loaded = "v001"

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
    import traceback
    s = traceback.format_exc()
    print("[pytoy]: Failed to Import.", e, s, flush=True)
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

" Virtual Environment handling.
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

" Open Terminal with the specified virtual environment.
function! pytoy#term()
python3 pytoy.term()
endfunction


" Related to ipython handling
function! pytoy#ipython_send_line()
python3 pytoy.ipython_send_line()
endfunction

function! pytoy#ipython_send_range()
python3 pytoy.ipython_send_range()
endfunction

function! pytoy#ipython_reset()
python3 pytoy.ipython_reset()
endfunction

function! pytoy#ipython_stop()
python3 pytoy.ipython_stop()
endfunction

function! pytoy#ipython_history()
python3 pytoy.ipython_history()
endfunction


" Related to Quickfix handling
function! pytoy#quickfix_gitfilter()
python3 pytoy.quickfix_gitfilter()
endfunction 

function! pytoy#quickfix_timesort()
python3 pytoy.quickfix_timesort()
endfunction 

