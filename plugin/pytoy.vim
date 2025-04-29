" Mapping definition 
nnoremap <leader>p :call pytoy#run()<CR>
nnoremap <leader>P :call pytoy#rerun()<CR>
nnoremap <expr><silent> <C-c> pytoy#is_running() ? pytoy#stop() : "\<C-c>"
nnoremap <leader>f :<c-u>call pytoy#ipython_send_line()<CR>
xnoremap <leader>f :<c-u>call pytoy#ipython_send_range()<CR>
nnoremap <leader>h :<c-u>call pytoy#ipython_history()<CR>
nnoremap <leader>t :<c-u>call pytoy#pytest_runfunc()<CR>
nnoremap <F12> :<c-u>call pytoy#uv_toggle()<CR>

call pytoy#init_python()
