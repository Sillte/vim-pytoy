" Mapping definition 
nnoremap <leader>p :call pytoy#run()<CR>
nnoremap <leader>P :call pytoy#rerun()<CR>
nnoremap <expr><silent> <C-c> pytoy#is_running() ? pytoy#stop() : "\<C-c>"
nnoremap <leader>f :<c-u>Console<CR>
xnoremap <leader>f :Console<CR>
nnoremap <leader>t :<c-u>Pytest<CR>
nnoremap <F12> :<c-u>UVToggle<CR>
nnoremap <leader>d :GotoDefinition<CR>
python3 import pytoy


