" Mapping definition 
nnoremap <leader>p :call pytoy#run()<CR>
nnoremap <leader>P :call pytoy#rerun()<CR>
nnoremap <leader>q :call pytoy#stop()<CR>
nnoremap <leader>f :<c-u>Console<CR>
xnoremap <leader>f :Console<CR>
nnoremap <leader>t :<c-u>Pytest<CR>
nnoremap <F12> :<c-u>UVToggle<CR>
nnoremap <leader>d :GotoDefinition<CR>
" It seems that invocation of the plugin is necessary.
call pytoy#init_python()
"python3 import pytoy 