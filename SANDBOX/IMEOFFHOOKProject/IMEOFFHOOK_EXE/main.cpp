#include <windows.h>
#include <tchar.h>

int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int) {
    
    HANDLE hMutex = CreateMutex(NULL, FALSE, _T("BEHOLD_IMEOFFHOOK_DLL_MUTEX_BY_SILLTE_AND_MIU_INOUE"));
    if (!hMutex) return 1;

    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        //MessageBox(NULL, _T("ä˘Ç…é¿çsíÜÇ≈Ç∑ÅB"), _T("IMEHook"), MB_OK | MB_ICONINFORMATION);
        return 0;
    }

    HMODULE dll = LoadLibrary(_T("IMEOFFHOOK_DLL.dll"));
    if (!dll) {
        //MessageBox(NULL, _T("DLLÇÃì«Ç›çûÇ›Ç…é∏îsÇµÇ‹ÇµÇΩ"), _T("IMEHook"), MB_OK | MB_ICONERROR);
        return 1;
    }

    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    FreeLibrary(dll);
    ReleaseMutex(hMutex);
    CloseHandle(hMutex);

    return 0;
}