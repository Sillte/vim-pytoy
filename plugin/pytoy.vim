" Mapping definition 
nnoremap <leader>p :call pytoy#run()<CR>
nnoremap <leader>P :call pytoy#rerun()<CR>
nnoremap <leader>q :call pytoy#stop()<CR>
nnoremap <leader>f :<c-u>Console<CR>
xnoremap <leader>f :Console<CR>
nnoremap <leader>t :<c-u>Pytest<CR>
" It seems that invocation of the plugin is necessary.
call pytoy#init_python()
