// 以下の ifdef ブロックは、DLL からのエクスポートを容易にするマクロを作成するための
// 一般的な方法です。この DLL 内のすべてのファイルは、コマンド ラインで定義された IMEOFFHOOKDLL_EXPORTS
// シンボルを使用してコンパイルされます。このシンボルは、この DLL を使用するプロジェクトでは定義できません。
// ソースファイルがこのファイルを含んでいる他のプロジェクトは、
// IMEOFFHOOKDLL_API 関数を DLL からインポートされたと見なすのに対し、この DLL は、このマクロで定義された
// シンボルをエクスポートされたと見なします。
#ifdef IMEOFFHOOKDLL_EXPORTS
#define IMEOFFHOOKDLL_API __declspec(dllexport)
#else
#define IMEOFFHOOKDLL_API __declspec(dllimport)
#endif

// このクラスは dll からエクスポートされました
class IMEOFFHOOKDLL_API CIMEOFFHOOKDLL {
public:
	CIMEOFFHOOKDLL(void);
	// TODO: メソッドをここに追加します。
};

extern IMEOFFHOOKDLL_API int nIMEOFFHOOKDLL;

IMEOFFHOOKDLL_API int fnIMEOFFHOOKDLL(void);
