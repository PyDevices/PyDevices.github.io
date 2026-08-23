#!/usr/bin/env python3
"""Serve the local PyDevices Pages workspace on one origin.

The organization portal is the default document root.  Pages sites published
by sibling repositories are mounted at their production URL prefixes.  A
mounted request first checks the repository's editable ``.site`` tree, then
falls back to the complete static tree stored on ``origin/gh-pages``.
"""

from __future__ import annotations

import argparse
from io import BytesIO
import mimetypes
from pathlib import Path, PurePosixPath
import subprocess
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit


PORTAL_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PORTAL_ROOT.parent
MOUNTS = {
    "mip": WORKSPACE_ROOT / "mip",
    "pydevices-examples": WORKSPACE_ROOT / "pydevices-examples",
}


class WorkspaceRequestHandler(SimpleHTTPRequestHandler):
    """Serve the portal plus sibling repositories' published Pages trees."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "credentialless")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-PyDevices-Server", "workspace")
        super().end_headers()

    def send_head(self):
        mounted = self._mounted_path()
        if mounted is None:
            return super().send_head()

        prefix, repo, relative = mounted
        if relative == PurePosixPath(".") or self.path.endswith("/"):
            relative = relative / "index.html"

        source_path = repo / ".site" / relative
        if source_path.is_file() and source_path.is_relative_to(repo / ".site"):
            return self._send_bytes(source_path.read_bytes(), str(source_path))

        git_path = relative.as_posix()
        result = subprocess.run(
            ["git", "-C", str(repo), "show", f"origin/gh-pages:{git_path}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return self._send_bytes(result.stdout, git_path)

        self.send_error(404, f"No local {prefix} publication for {git_path}")
        return None

    def _mounted_path(self):
        raw_path = unquote(urlsplit(self.path).path)
        parts = PurePosixPath(raw_path).parts
        if len(parts) < 2 or parts[0] != "/" or parts[1] not in MOUNTS:
            return None
        if any(part in {".", ".."} for part in parts[2:]):
            self.send_error(400, "Invalid path")
            return None
        prefix = parts[1]
        return prefix, MOUNTS[prefix], PurePosixPath(*parts[2:])

    def _send_bytes(self, data: bytes, filename: str):
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Last-Modified", self.date_time_string())
        self.end_headers()
        return BytesIO(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    handler = partial(WorkspaceRequestHandler, directory=str(PORTAL_ROOT))
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    print(f"Serving PyDevices workspace at http://{args.bind}:{server.server_port}/")
    print("  /                    -> PyDevices.github.io")
    print("  /mip/                -> mip/.site + origin/gh-pages")
    print("  /pydevices-examples/ -> pydevices-examples/.site + origin/gh-pages")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
