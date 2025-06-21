// dllmain.cpp : DLL アプリケーションのエントリ ポイントを定義します。
#include "pch.h"
#include "windows.h"
#include "imm.h"

HHOOK hHook = NULL;


LRESULT CALLBACK KeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION && wParam == WM_KEYDOWN) {
        auto p = (KBDLLHOOKSTRUCT*)lParam;
        bool wantNonConv = false;

        // ESC が押されたとき
        if (p->vkCode == VK_ESCAPE) {
            wantNonConv = true;
        }
        // Ctrl + C が押されたとき
        else if ((p->vkCode == 'C') && (GetAsyncKeyState(VK_CONTROL) & 0x8000)) {
            wantNonConv = true;
        }

        if (wantNonConv) {
            INPUT inputs[2] = {};
            inputs[0].type = INPUT_KEYBOARD;
            inputs[0].ki.wVk = VK_NONCONVERT;

            inputs[1].type = INPUT_KEYBOARD;
            inputs[1].ki.wVk = VK_NONCONVERT;
            inputs[1].ki.dwFlags = KEYEVENTF_KEYUP;

            SendInput(2, inputs, sizeof(INPUT));
        }
    }
    return CallNextHookEx(hHook, nCode, wParam, lParam);
}

BOOL APIENTRY DllMain(HMODULE hModule,
    DWORD  ul_reason_for_call,
    LPVOID lpReserved
)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
        hHook = SetWindowsHookEx(WH_KEYBOARD_LL, KeyboardProc, hModule, 0);
        break;
    case DLL_PROCESS_DETACH:
        UnhookWindowsHookEx(hHook);
        break;
    }
    return TRUE;
}

