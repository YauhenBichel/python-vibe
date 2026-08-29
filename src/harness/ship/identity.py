"""The GitHub identity python-vibe adds when it is used.

The person who ran the tool stays the commit author. When the harness
writes a commit or opens a pull request, it adds this account as
co-author so GitHub shows it on that change. The account is created
once at github.com/signup; this module only writes the trailer.
"""

from __future__ import annotations

import os
import re

CO_AUTHOR_LOGIN = "python-vibe"
CO_AUTHOR_NAME = "python-vibe"
CO_AUTHOR_EMAIL = "python-vibe@users.noreply.github.com"
CO_AUTHOR_URL = "https://github.com/python-vibe"
# Set once the account exists, to the address GitHub lists for it under
# Settings, Emails, for example:
#   export PYTHON_VIBE_COAUTHOR="python-vibe <1234567+python-vibe@users.noreply.github.com>"
COAUTHOR_ENV = "PYTHON_VIBE_COAUTHOR"


def co_author_line() -> str:
    """The trailer written on a commit python-vibe made.

    Casing does not decide whether GitHub links it; owning the address
    does. Until the account exists the trailer still records who did the
    work, it simply shows no avatar.
    """
    identity = os.environ.get(COAUTHOR_ENV, "").strip()
    if identity:
        return f"Co-authored-by: {identity}"
    return f"Co-authored-by: {CO_AUTHOR_NAME} <{CO_AUTHOR_EMAIL}>"


def co_author_email() -> str:
    identity = os.environ.get(COAUTHOR_ENV, "").strip()
    match = re.search(r"<([^>]+)>", identity) if identity else None
    return match.group(1) if match else CO_AUTHOR_EMAIL


def co_author_links() -> bool:
    """Whether GitHub can turn the trailer into a linked account.

    A `users.noreply.github.com` address links only with the account's
    numeric id in front of the name. The bare form was issued to older
    accounts and links only if that account still holds it.
    """
    email = co_author_email()
    if not email.endswith("@users.noreply.github.com"):
        return "@" in email and "." in email.split("@")[-1]
    return bool(re.match(r"\d+\+", email))


def with_co_author(message: str) -> str:
    """Append the trailer once, when python-vibe made the commit."""
    text = message.rstrip()
    if "co-authored-by: python-vibe" in text.lower():
        return text
    return f"{text}\n\n{co_author_line()}\n"
