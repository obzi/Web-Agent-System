from __future__ import annotations

import base64
import os
from typing import Any

import httpx

from utils.logger import log


API = "https://api.github.com"


def _headers() -> dict[str, str]:
    token = os.environ["GITHUB_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _owner() -> str:
    return os.environ.get("GITHUB_OWNER", "obzi")


def ensure_repo(slug: str, *, private: bool = True, description: str = "") -> str:
    """Ensure repo exists; return clone URL."""
    repo = f"preview-{slug}"
    owner = _owner()
    with httpx.Client(timeout=30.0, headers=_headers()) as http:
        resp = http.get(f"{API}/repos/{owner}/{repo}")
        if resp.status_code == 200:
            return resp.json()["html_url"]

        # Try user endpoint first; fall back to org.
        create_user = http.post(
            f"{API}/user/repos",
            json={"name": repo, "private": private, "description": description, "auto_init": True},
        )
        if create_user.status_code in (200, 201):
            return create_user.json()["html_url"]
        create_org = http.post(
            f"{API}/orgs/{owner}/repos",
            json={"name": repo, "private": private, "description": description, "auto_init": True},
        )
        create_org.raise_for_status()
        return create_org.json()["html_url"]


def put_file(slug: str, path: str, content: str, message: str) -> None:
    repo = f"preview-{slug}"
    owner = _owner()
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    with httpx.Client(timeout=30.0, headers=_headers()) as http:
        # Check for existing SHA
        existing = http.get(f"{API}/repos/{owner}/{repo}/contents/{path}")
        body: dict[str, Any] = {"message": message, "content": b64, "branch": "main"}
        if existing.status_code == 200:
            body["sha"] = existing.json().get("sha")
        resp = http.put(f"{API}/repos/{owner}/{repo}/contents/{path}", json=body)
        if resp.status_code not in (200, 201):
            log("github.put_failed", slug=slug, path=path, status=resp.status_code, body=resp.text[:400])
            resp.raise_for_status()


def push_site(slug: str, html: str, content_json: dict) -> str:
    import json as _json

    repo_url = ensure_repo(slug, description=f"RapidLocalSites preview for {slug}")
    put_file(slug, "index.html", html, f"generate preview for {slug}")
    put_file(slug, "content.json", _json.dumps(content_json, ensure_ascii=False, indent=2), f"content.json for {slug}")
    return repo_url
