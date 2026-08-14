import threading


class LLMImportResolver:
    """Import llm-related libraries in the background to avoid blocking plugin startup.
    """
    
    def __init__(self, moratorium_time: float = 1.0) -> None:
        self._moratorium_time = moratorium_time
        self._import_done: threading.Event | None = None
        self._lock = threading.Lock()
        self._imported: bool = False
        self._import_error: ImportError | None = None

        self._moratorium_event = threading.Event()


    def import_background(self) -> None:
        with self._lock:
            if self._import_done is not None:
                return 

            event = self._import_done = threading.Event()

        def _inner():
            self._moratorium_event.wait(self._moratorium_time)
            try:
                self._naive_import()
            finally:
                event.set()

        threading.Thread(
            target=_inner,
            daemon=True,
        ).start()

    def notify_capacity(self) -> None:
        self._moratorium_event.set()
        
    def ensure_import(self) -> None:
        with self._lock:
            if self._imported:
                return 

            event = self._import_done

        if event is not None:
            event.wait()
        else:
            self._naive_import()

        if self._import_error:
            raise self._import_error

    def _naive_import(self) -> None:
        try:
            import litellm
            from pytoy_llm import completion, run
            self._imported = True
        except ImportError as e:
            from pathlib import Path 
            Path("_llm_import_error.txt").write_text(str(e))
            self._import_error = e

    @property
    def import_error(self) -> ImportError | None:
        self.ensure_import()
        return self._import_error


if __name__ == "__main__":
    resolver = LLMImportResolver()
    resolver.import_background()
    resolver.ensure_import()
