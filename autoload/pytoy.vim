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

function! pytoy#reset()
python3 pytoy.reset()
endfunction

function! pytoy#plugin_root() abort
    let l:path = fnamemodify(expand('<sfile>:p'), ':h')

    while l:path !=# fnamemodify(l:path, ':h')
        if filereadable(l:path . '/pyproject.toml')
            return l:path
        endif

        let l:path = fnamemodify(l:path, ':h')
    endwhile

    echohl ErrorMsg
    echom '[pytoy] Failed to find pyproject.toml'
    echohl None

    return ''
endfunction

function! pytoy#pyproject() abort
    let l:root = pytoy#plugin_root()
    if empty(l:root)
        return ''
    endif

    let l:path = l:root . '/pyproject.toml'

    if !filereadable(l:path)
        echohl ErrorMsg
        echom '[pytoy] pyproject.toml was not found.' . l:path
        echohl None
        return ''
    endif
    return l:path

endfunction

function! pytoy#find_python_executable() abort
    if !has('python3')
        echohl ErrorMsg
        echom '[pytoy] This Vim/Neovim was built without Python 3 support.'
        echohl None
        return ''
    endif

    try
        let l:executable = py3eval('sys.executable')
        let l:prefix = py3eval('sys.prefix')
        let l:base_prefix = py3eval('getattr(sys, "base_prefix", "")')
    catch
        echohl ErrorMsg
        echom '[pytoy] Failed to inspect the Python 3 environment: ' . v:exception
        echohl None
        return ''
    endtry

    " sys.executable is usable when it points to an actual Python executable.
    if !empty(l:executable) && executable(l:executable)
        let l:executable_name = fnamemodify(l:executable, ':t')

        if l:executable_name =~? '^python\%(\d\+\)\?\%(\.exe\)\?$'
            return fnamemodify(l:executable, ':p')
        endif
    endif

    " Search for Python from sys.prefix.
    if !empty(l:prefix)
        let l:candidates = []

        if has('win32') || has('win64')
            let l:candidates = [
                        \ l:prefix . '/Scripts/python.exe',
                        \ l:prefix . '/python.exe',
                        \ ]
        else
            let l:candidates = [
                        \ l:prefix . '/bin/python3',
                        \ l:prefix . '/bin/python',
                        \ ]
        endif

        for l:candidate in l:candidates
            if executable(l:candidate)
                return fnamemodify(l:candidate, ':p')
            endif
        endfor
    endif

    echohl ErrorMsg
    echom '[pytoy] Python 3 executable was not found.'
    echom '[pytoy] sys.prefix      = ' . string(l:prefix)
    echom '[pytoy] sys.base_prefix = ' . string(l:base_prefix)
    echom '[pytoy] sys.executable  = ' . string(l:executable)
    echohl None

    return ''
endfunction

function! pytoy#update_python_environment(...) abort
    let l:python = pytoy#find_python_executable()
    if empty(l:python)
        return 0
    endif

    let l:pyproject = pytoy#pyproject()
    if empty(l:pyproject)
        return 0
    endif

    let l:uv = exepath('uv')
    if empty(l:uv)
        echohl ErrorMsg
        echom '[pytoy] uv was not found in PATH.'
        echohl None
        return 0
    endif

    let l:args = [
                \ l:uv,
                \ 'pip',
                \ 'install',
                \ '-r',
                \ l:pyproject,
                \ '--python',
                \ l:python,
                \ ]

    if a:0 > 0
        call extend(l:args, a:000)
    endif

    let l:command = join(map(copy(l:args), 'shellescape(v:val)'), ' ')
    echom l:command

    if has('nvim')
        let l:output = system(l:args)
    else
        let l:output = system(l:command)
    endif

    let l:status = v:shell_error

    if l:status != 0
        echohl ErrorMsg

        echom '[pytoy] uv install failed (exit ' . l:status . '): ' . trim(l:output)

        if l:output =~? 'os error 5\|access is denied'
            echom '[pytoy] Access to the Python environment was denied.'
            echom '[pytoy] The current Vim process may not have sufficient privileges.'
            echom '[pytoy] Run Vim with administrator privileges, or execute the following command'
            echom '[pytoy] manually from an administrator command prompt:'
            echom l:command
        elseif l:status == 2
            echom '[pytoy] uv reported a general error.'
        endif

        echohl None
        return 0
    endif

    echom '[pytoy] Python dependencies installed successfully: ' . string(l:python)
    echom '[pytoy] Please restart Vim/Neovim to reload the Python environment.'
    return 1
endfunction