"""
Portal Configuration — 5L-TEP Layer 4 Toolkit
==============================================
*Which* CKAN portal this repository monitors lives in `portal.json` at the
repository root: its "portal_url" is the only value an instance for another
portal has to change (the same convention as the Layer 1 toolkit). Keeping it
in a versioned file, rather than in a repository variable, makes the
difference between two instances visible in git.

Precedence: an explicit URL (``main.py --portal``) > the environment variable
CKAN_PORTAL_URL > portal.json. In GitHub Actions the workflows pass the
repository variable CKAN_PORTAL_URL (the adoption path described in the WFA
2026 paper: fork, set one repository variable, enable Actions); when it is not
set, the variable is empty and portal.json applies.

Part of the 5L-TEP Layer 4 (Observability & Provenance) Toolkit.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

PORTAL_FILE = Path(__file__).resolve().parent.parent / "portal.json"


def load_portal(url: Optional[str] = None, path: Path = PORTAL_FILE) -> Dict[str, str]:
    """Return {"portal_url", "name", "title"} for the monitored portal.

    ``name`` and ``title`` come from portal.json only when the URL in use is
    the one it declares; otherwise both fall back to the URL's host.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}
    declared = (raw.get("portal_url") or "").rstrip("/")
    chosen = (url or os.environ.get("CKAN_PORTAL_URL") or declared).rstrip("/")
    if not chosen.startswith(("https://", "http://")):
        raise ValueError('portal.json must give the portal\'s root URL in "portal_url"')
    host = urlparse(chosen).hostname or chosen
    same = chosen == declared
    return {
        "portal_url": chosen,
        "name": (raw.get("name") if same else None) or host,
        "title": (raw.get("title") if same else None) or host,
    }
