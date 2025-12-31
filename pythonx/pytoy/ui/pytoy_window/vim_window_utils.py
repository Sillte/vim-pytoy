from pytoy.infra.core.models import CursorPosition, CharacterRange
import vim  # (vscode-neovim extention)
from typing import Sequence


def get_last_selection(winid: int) -> CharacterRange | None:
    """Return the last selection of `CharacterRange`, if exist.  
    Otherwise, return None.

    Args:
        `lines`: `buffer.lines`. Here, to calibrate the col of CursorPosition, `lines` info is necessary.
    """
    if not winid:
        return None
    bufnr = int(vim.eval(f"winbufnr({winid})"))
    if bufnr <= 0:
        return None
    target_buffer = vim.buffers[bufnr]

    def _get_pos(winid: int, mark: str="'<") -> tuple[int, int, int, int]:
        vim.command(f"""let g:_pytoy_get_pos_tempory_arg="{mark}" """)
        cmd = "let g:_pytoy_get_pos_temporary_return = getpos(g:_pytoy_get_pos_tempory_arg)"
        vim.command(f"""call win_execute({winid}, "{cmd}")""")
        return tuple(vim.vars['_pytoy_get_pos_temporary_return'])

    def _from_vim_coords(vim_line: int, vim_col: int) -> CursorPosition:
        """Solves
        1. 1-base -> 0-base
        2. handling of bytes.
        """
        n_line = max(0, vim_line - 1)
        line_content = target_buffer[n_line]
        line_bytes = line_content.encode('utf-8')
        byte_offset = min(vim_col - 1, len(line_bytes))  # 0-based and to be safe.
        res_col = len(line_bytes[:byte_offset].decode('utf-8', errors='ignore'))
        return CursorPosition(n_line, res_col)
    s_pos = _get_pos(winid, "'<")
    e_pos = _get_pos(winid, "'>")
    mode = vim.eval(f"""win_execute({winid}, "echo visualmode()")""").strip()

    match mode:
        case "v":
            # Visual Mode
            # `CharacterRange` is exclusize.
            p1 = _from_vim_coords(s_pos[1], s_pos[2])
            p2_inclusive = _from_vim_coords(e_pos[1], e_pos[2])
            p2 = CursorPosition(p2_inclusive.line, p2_inclusive.col + 1)
            return CharacterRange(p1, p2)
        case "V" | "\x16":
            # Line Visual Mode or Block Visual Mode
            p1 = CursorPosition(s_pos[1] - 1, 0)
            p2 = CursorPosition(e_pos[1], 0) # 0-based, and next line's start.
            return CharacterRange(p1, p2)
    return None
