" Mapping definition 
nnoremap \p :call pytoy#run()<CR>
nnoremap \P :call pytoy#rerun()<CR>
nnoremap <expr><silent> <C-c> pytoy#is_running() ? pytoy#stop() : "\<C-c>"
nnoremap <leader>f :<c-u>call pytoy#ipython_send_line()<CR>
xnoremap <leader>f :<c-u>call pytoy#ipython_send_range()<CR>
nnoremap <leader>h :<c-u>call pytoy#ipython_history()<CR>

call pytoy#init_python()
