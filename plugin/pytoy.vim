" Mapping definition
nnoremap <leader>p :call pytoy#run()<CR>
nnoremap <leader>P :call pytoy#rerun()<CR>
nnoremap <leader>q :call pytoy#stop()<CR>
nnoremap <leader>f :<c-u>Console<CR>
xnoremap <leader>f :Console<CR>
nnoremap <leader>t :<c-u>Pytest<CR>

" Commands
command! -nargs=* PytoyUpdate
            \ call pytoy#update_python_environment(<f-args>)

" Initialize the Python side of pytoy.
call pytoy#init_python()