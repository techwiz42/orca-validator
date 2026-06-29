"""Resolve CriticMarkup-style redline markup into a clean document.

The model emits `{--removed--}` and `{++added++}`. The UI renders those as red/green; the
downloadable .md/.docx get the *accepted* version (deletions dropped, insertions kept).
"""
import re

_DEL = re.compile(r"\{--([\s\S]*?)--\}")
_INS = re.compile(r"\{\+\+([\s\S]*?)\+\+\}")
_STRAY = re.compile(r"\{--|--\}|\{\+\+|\+\+\}")  # leftover unbalanced markers (model sloppiness)


def clean_revision(redline: str | None) -> str:
    if not redline:
        return ""
    text = _DEL.sub("", redline)        # drop removed text
    text = _INS.sub(r"\1", text)        # keep added text
    return _STRAY.sub("", text)         # strip any stray/unbalanced markers
