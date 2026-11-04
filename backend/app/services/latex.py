"""Repair LaTeX that lost its backslashes on the way through JSON.

Models write their structured output as JSON text, where a backslash starts
an escape. One that forgets to double it turns "\\frac" into a form feed
followed by "rac", "\\theta" into a tab and "heta", "\\beta" into a backspace
and "eta". The control characters are never legitimate in revision text, so
they can be turned back into the command they came from.
"""

import re

# Form feed and backspace never belong in revision text, so they always go back.
_ALWAYS = {"\x0c": "\\f", "\x08": "\\b"}
# Tab and carriage return do occur legitimately, so only when a LaTeX command
# name follows: \theta, \times, \tau, \rho, \right.
_BEFORE_LETTERS = re.compile(r"[\t\r](?=[a-zA-Z]{2,})")
# A newline is ordinary punctuation outside mathematics, so it is only
# repaired inside $...$, where \nabla, \neq and \nu are the likely cause.
_MATH = re.compile(r"\$\$.+?\$\$|\$[^$]+\$", re.S)
# The rest of each LaTeX command that starts with "n".
_NEWLINE_COMMAND = re.compile(r"\n(?=(?:abla|eq|e|u|ot|eg|i|mid|leq|geq|ewline)(?![a-zA-Z]))")


def repair(text: str) -> str:
    if not text:
        return text
    for broken, command in _ALWAYS.items():
        text = text.replace(broken, command)
    text = _BEFORE_LETTERS.sub(lambda m: "\\t" if m.group(0) == "\t" else "\\r", text)
    return _MATH.sub(lambda m: _NEWLINE_COMMAND.sub(r"\\n", m.group(0)), text)
