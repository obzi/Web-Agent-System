from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from utils.logger import log


API = "https://api.vercel.com"


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {os.environ['VERCEL_TOKEN']}"}


def _team_param() -> dict[str, str]:
    team = os.environ.get("VERCEL_TEAM_ID")
    return {"teamId": team} if team else {}


def _owner() -> str:
    return os.environ.get("GITHUB_OWNER", "obzi")


def deploy_preview(slug: str) -> str:
    """Create (or ensure) a Vercel project linked to the GitHub repo; trigger deploy; return URL."""
    project_name = f"preview-{slug}"
    repo = f"{_owner()}/preview-{slug}"

    with httpx.Client(timeout=60.0, headers=_headers(), params=_team_param()) as http:
        # Create project if missing (idempotent-ish: 409 = already exists).
        create = http.post(
            f"{API}/v10/projects",
            json={
                "name": project_name,
                "gitRepository": {"type": "github", "repo": repo},
                "framework": None,
            },
        )
        if create.status_code not in (200, 201, 409):
            log("vercel.create_failed", status=create.status_code, body=create.text[:400])
            create.raise_for_status()

        # Trigger a deployment from main.
        deploy = http.post(
            f"{API}/v13/deployments",
            json={
                "name": project_name,
                "gitSource": {"type": "github", "repo": repo, "ref": "main"},
                "target": "production",
                "projectSettings": {"framework": None},
            },
        )
        deploy.raise_for_status()
        data = deploy.json()
        url = data.get("url") or data.get("alias", [None])[0]
        if not url:
            raise RuntimeError(f"Vercel did not return a URL: {data}")
        return f"https://{url}" if not url.startswith("http") else url


def list_projects() -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    with httpx.Client(timeout=30.0, headers=_headers(), params=_team_param()) as http:
        next_cursor: str | None = None
        while True:
            params = {"limit": 100}
            if next_cursor:
                params["until"] = next_cursor
            resp = http.get(f"{API}/v9/projects", params=params)
            resp.raise_for_status()
            body = resp.json()
            projects.extend(body.get("projects", []))
            pagination = body.get("pagination", {})
            next_cursor = pagination.get("next")
            if not next_cursor:
                break
    return projects


def delete_project(project_id: str) -> None:
    with httpx.Client(timeout=30.0, headers=_headers(), params=_team_param()) as http:
        resp = http.delete(f"{API}/v9/projects/{project_id}")
        if resp.status_code not in (200, 204):
            log("vercel.delete_failed", project_id=project_id, status=resp.status_code, body=resp.text[:400])


def cleanup_old_previews(ttl_days: int) -> list[str]:
    """Delete preview-* projects older than ttl_days. Returns slugs that were cleaned up."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
    cleaned: list[str] = []
    for project in list_projects():
        name = project.get("name", "")
        if not name.startswith("preview-"):
            continue
        created_ms = project.get("createdAt") or 0
        created = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
        if created < cutoff:
            delete_project(project["id"])
            cleaned.append(name.replace("preview-", "", 1))
            log("vercel.cleanup", project=name, created=created.isoformat())
    return cleaned
