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
    msg = "[pytoy]: Failed to import pytoy.\n{}".format(s.replace('"', "'"))
    vim.command('echohl ErrorMsg | echom "{}" | echohl None'.format(msg))
    print(msg)
    raise e
else:
    vim.command("let s:init_python=1")
EOF
endfunction

function! pytoy#reset_python()
python3 pytoy.reset_python()
endfunction


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
  return py3eval('pytoy.is_running()')
endfunction

function! pytoy#reset()
python3 pytoy.reset()
endfunction


