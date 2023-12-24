from typing import Callable


def apply(data: dict, *funcs: Callable[[dict, tuple], None]) -> dict:
    for func in funcs:
        _apply(data, func)
    return data


def _apply(data: dict, func: Callable[[dict, tuple], None]) -> dict:
    for key in set(data.keys()):
        val = data[key]
        if isinstance(val, dict):
            apply(val, func)
        elif isinstance(val, list):
            l = []
            for el in val:
                if isinstance(el, dict):
                    apply(el, func)
                if el:
                    l.append(el)
            if l:
                val, data[key] = l, l
            else:
                val = None

        if val:
            func(data, (key, val))
        else:
            del data[key]
    return data
