if exists('g:loaded_pytoy') || &cp
    finish
endif
let g:loaded_pytoy = 1
let g:pytoy_loaded = 'v001'

" ---------------------------------------------------------------------------
" Constants
" ---------------------------------------------------------------------------

let s:autoload_dir = fnamemodify(expand('<sfile>:p'), ':h')

" ---------------------------------------------------------------------------
" Utilities
" ---------------------------------------------------------------------------

function! s:error(message) abort
    echohl ErrorMsg
    for l:line in split(a:message, "\n")
        echom '[pytoy] ' . l:line
    endfor
    echohl None
endfunction

function! s:find_project_root(start) abort
    let l:path = a:start

    while l:path !=# fnamemodify(l:path, ':h')
        if filereadable(l:path . '/pyproject.toml')
            return l:path
        endif

        let l:path = fnamemodify(l:path, ':h')
    endwhile

    return ''
endfunction

function! s:shell_command(args) abort
    return join(map(copy(a:args), 'shellescape(v:val)'), ' ')
endfunction

function! s:run_command(args) abort
    if has('nvim')
        let l:output = system(a:args)
    else
        let l:output = system(s:shell_command(a:args))
    endif

    return {
        \ 'output': l:output,
        \ 'status': v:shell_error,
        \ }
endfunction

" ---------------------------------------------------------------------------
" Python initialization
" ---------------------------------------------------------------------------

function! pytoy#init_python() abort
    let g:pytoy_python_initialized = 0
    if !has('python3')
        call s:error('Vim/Neovim was built without Python 3 support.')
        return 0
    endif

    python3 << EOF
import os
import sys
import traceback
import vim

plugin_dir = os.path.dirname(vim.eval("expand('<sfile>:p:h')"))
pythonx_dir = os.path.join(plugin_dir, "pythonx")

if pythonx_dir not in sys.path:
    sys.path.append(pythonx_dir)

try:
    import pytoy
except Exception:
    message = (
        "[pytoy] Failed to import pytoy.\n"
        + traceback.format_exc()
    )
    vim.command(
        "call pytoy#_python_error({})".format(repr(message))
    )
    raise
else:
    vim.command("let g:pytoy_python_initialized = 1")
EOF

    return get(g:, 'pytoy_python_initialized', 0)
endfunction

function! pytoy#_python_error(message) abort
    call s:error(a:message)
endfunction

" ---------------------------------------------------------------------------
" Python commands
" ---------------------------------------------------------------------------

function! pytoy#run() abort
    python3 pytoy.run()
endfunction

function! pytoy#rerun() abort
    python3 pytoy.rerun()
endfunction

function! pytoy#stop() abort
    python3 pytoy.stop()
endfunction

function! pytoy#reset() abort
    python3 pytoy.reset()
endfunction

" ---------------------------------------------------------------------------
" Project files
" ---------------------------------------------------------------------------

function! pytoy#plugin_root() abort
    let l:root = s:find_project_root(s:autoload_dir)

    if empty(l:root)
        call s:error('Failed to find pyproject.toml.')
    endif

    return l:root
endfunction

function! pytoy#pyproject() abort
    let l:root = pytoy#plugin_root()

    if empty(l:root)
        return ''
    endif

    return l:root . '/pyproject.toml'
endfunction

" ---------------------------------------------------------------------------
" Find environment
" ---------------------------------------------------------------------------

function! s:find_python_venv() abort
    if !has('python3')
        call s:error('Vim/Neovim was built without Python 3 support.')
        return ''
    endif

    try
        python3 << EOF
import os
import sys

venv_path = None

for path in reversed(sys.path):
    if not path:
        continue

    current = os.path.realpath(path)

    if os.path.basename(current).lower() != "site-packages":
        continue

    while True:
        if os.path.isfile(os.path.join(current, "pyvenv.cfg")):
            venv_path = current
            break

        parent = os.path.dirname(current)

        if parent == current:
            break

        current = parent

    if venv_path:
        break

vim.command(
    "let g:pytoy_python_venv = " + repr(venv_path or "")
)
EOF
    catch
        call s:error(
                    \ 'Failed to detect Python virtual environment: '
                    \ . v:exception
                    \ )
        return ''
    endtry
    return get(g:, 'pytoy_python_venv', '')
endfunction

" ---------------------------------------------------------------------------
" Python environment update
" ---------------------------------------------------------------------------

function! pytoy#update_python_environment(...) abort
    let l:python_venv = s:find_python_venv()
    if empty(l:python_venv)
        return 0
    endif

    if has('win32') || has('win64')
        let l:python = l:python_venv . '/Scripts/python.exe'
    else
        let l:python = l:python_venv . '/bin/python'
    endif

    if !executable(l:python)
        call s:error('Python executable was not found: ' . l:python)
        return 0
    endif

    let l:pyproject = pytoy#pyproject()
    if empty(l:pyproject)
        return 0
    endif

    let l:uv = exepath('uv')
    if empty(l:uv)
        call s:error('uv was not found in PATH.')
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

    call s:append_upgrade_option(l:args, a:000)

    let l:command = s:shell_command(l:args)
    echom l:command

    let l:result = s:run_command(l:args)

    if l:result.status != 0
        call s:report_uv_error(l:result, l:command)
        return 0
    endif

    echom '[pytoy] Python dependencies installed successfully: '
                \ . string(l:python_venv)
    echom '[pytoy] Please restart Vim/Neovim to reload the Python environment.'

    return 1
endfunction

function! s:append_upgrade_option(args, user_args) abort
    if index(a:user_args, '--upgrade') < 0
                \ && index(a:user_args, '--no-upgrade') < 0
        call add(a:args, '--upgrade')
    endif

    call extend(a:args, a:user_args)
endfunction

function! s:report_uv_error(result, command) abort
    call s:error(
                \ 'uv install failed (exit '
                \ . a:result.status
                \ . '): '
                \ . trim(a:result.output)
                \ )

    if a:result.output =~? 'os error 5\|access is denied'
        echom '[pytoy] Access to the Python environment was denied.'
        echom '[pytoy] The current Vim process may not have sufficient privileges.'
        echom '[pytoy] Run Vim with administrator privileges, or execute this command manually:'
        echom a:command
    elseif a:result.status == 2
        echom '[pytoy] uv reported a general error.'
    endif
endfunction