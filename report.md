調査メモ:

(open_window) の処理が遅れるくだりについての調査メモ

- VSCode側 showTextDocument 自体は約30ms程度
- END RPC REQUEST後、Neovimイベント発火まで約100〜200ms
- BufferProviderはDocument生成を担当しているが、Window同期は別経路
- BufferManager周辺のlayout同期が怪しい
- syncEditorLayoutDebounced = debounce(syncEditorLayout,100ms)
  が存在する
- wait_until_trueを短くしてもイベント待ち部分が原因なら意味は薄い
- 現状は100ms程度の遅延を前提に進める