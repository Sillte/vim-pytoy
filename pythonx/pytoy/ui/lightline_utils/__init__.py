"""Personal utility functions for using `lightline`.

This module assumes the following plugin is already installed. 
* https://github.com/itchyny/lightline.vim

Policy
------

Note
----------------
This is an inefficient wrapper, yet.


Copyright of `lightline`.:

* https://github.com/itchyny/lightline.vim
* Copyright: Copyright (c) 2013-2020 itchyny

Thank you for the great plugin! 
"""

import vim
from typing import Callable
from pytoy.ui.lightline_utils._lightline import _Lightline
from pytoy.infra.vim_function import PytoyVimFunctions


class LightlineUser:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.lightline = _Lightline()
        self._infos = dict()
        self._initialized = True

    def _to_funcname(self, func):
        if callable(func):
            vimfunc_name = PytoyVimFunctions.register(func)
            vim.command(f"echo exists('{vimfunc_name}')")
            vim.command(f"echo exists('g:lightline')")
        else:
            vimfunc_name = func
        return vimfunc_name

    def register(
        self, func, mode="active", direction="left", level=-1, index=None, name=None
    ):
        """Register `func`.

        Args:
            func (str or function): the target funciton.
            mode(str): "active" or "inactive"
            direction(str): "left" or "right"
            level(int): the index of `self[{mode}][{direction}]`, which represents the group
            index(int, None): If non-negative interger is specified, then inserted to `self[{mode}][{direction}][{index}]`.

        Return (str):
            key of registration, which equals to `vim-function` name.

        Note
        ----------------------------------------------------------------------------
        It is intended that `self` is regarded as ``g:lightline``.
        """
        assert mode in {"active", "inactive"}
        assert direction in {"left", "right"}

        key = self._to_funcname(func)

        if key in self._infos:
            self.deregister(key)

        if name is None:
            name = key

        targets = self.lightline[mode][direction]
        n_level = len(targets)
        if 0 <= level < n_level:
            if index is None:
                targets[level].append(name)
            else:
                targets[level].insert(index, name)
        else:
            targets.append([name])

        # Register about `component`.
        if PytoyVimFunctions.is_registered(key):
            c_type = "component_function"
        else:
            c_type = "component"
        self.lightline[c_type][name] = key

        info = dict()
        info["name"] = name
        info["key"] = key
        info["component_type"] = c_type
        self._infos[key] = info

        self.lightline.update()
        self.lightline.enable()

        return key

    def deregister(self, key, strict_error=False):
        """Deregister function.

        Args:
            key (str, function): key of registration, which is the same as vim-function name.
            strict_error(bool): If `True` and `key` is not existent, raise `ValueError`.

        Raise:
            ValueError:

        """
        key = self._to_funcname(key)
        if key not in self._infos:
            if strict_error:
                raise ValueError(f"`{key}` is not existent.")
            else:
                return

        # Deregister about `name`.
        info = self._infos[key]
        name = info["name"]
        for mode in ("active", "inactive"):
            for direction in ("left", "right"):
                self.lightline[mode][direction] = [
                    [elem for elem in sub if elem != name]
                    for sub in self.lightline[mode][direction]
                ]

        # Deregister about `component` / `component_function`.
        # Register about `component`.
        if PytoyVimFunctions.is_registered(key):
            c_type = "component_function"
        else:
            c_type = "component"
        del self.lightline[c_type][name]
        # print("self[c_type]", self[c_type])

        # Deletion of `key`.
        del self._infos[key]

        self.lightline.update()
        self.lightline.enable()

    def is_registered(self, key):
        key = self._to_funcname(key)
        return key in self._infos


lightline_user = LightlineUser()


def register(
    func: str | Callable,
    mode: str = "active",
    direction: str = "left",
    level: int = -1,
    index: int | None = None,
    name: str | None = None,
):
    return lightline_user.register(func, mode, direction, level, index, name)

def deregister(
    key: str | Callable,
    strict_error: bool = False,
):
    return lightline_user.deregister(key, strict_error)

def is_registered(key: str | Callable):
    return lightline_user.is_registered(key)