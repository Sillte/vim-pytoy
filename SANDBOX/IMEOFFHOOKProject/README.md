# IMEOFFHOOK

## Desired states

In VIM/NEOVIM/VSCODE-NEOVIM extension, I want IME function to be OFF automatically when I return to `NORMAL` mode.

Though, it is relatively easy to realize this in VIM with `autocmd` and `iminsert`,
**for my environment** it seems difficult to apply it in VSCODE + NEOVIM EXTENSION.

## Procedures

* [Prerequisite]:  Please set "無変換キー" s `IME off` function in control panel of Windows.
* Execute `IMEOFFHOOK_EXE.exe` in `DIST` folder.

## What `IMEOFFHOOK_DLL` will do.

* Use Global KeyHook and monitor the messages of keyboards.
* Whenever `ESC` or `CTRL+C` are captured, it will send key push of "無変換キー".

## Comments

* When you build the solution, if `IMEOFFHOOK_EXE.exe` is running, it naturally causes errors.
    - Beforehand, please shutdown `IMEOFFHOOK_EXE.exe`. 
