"""GitHub adapter — implements ISourceControlPort using the GitHub REST API."""

from __future__ import annotations

import logging
from base64 import b64encode

import httpx

from src.config import settings
from src.core.models import GeneratedFile
from src.core.ports import ISourceControlPort

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubAdapter(ISourceControlPort):
    """Manages branches, commits, and PRs via the GitHub REST API."""

    def __init__(self) -> None:
        self._owner = settings.github_repo_owner
        self._repo = settings.github_repo_name
        self._base = settings.github_target_branch
        self._headers = {
            "Authorization": f"Bearer {settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    @property
    def _repo_url(self) -> str:
        return f"{GITHUB_API}/repos/{self._owner}/{self._repo}"

    async def create_branch(self, branch_name: str) -> str:
        async with httpx.AsyncClient() as client:
            # Get the SHA of the base branch
            resp = await client.get(
                f"{self._repo_url}/git/ref/heads/{self._base}",
                headers=self._headers,
            )
            resp.raise_for_status()
            sha = resp.json()["object"]["sha"]

            # Create the new branch
            resp = await client.post(
                f"{self._repo_url}/git/refs",
                headers=self._headers,
                json={"ref": f"refs/heads/{branch_name}", "sha": sha},
            )
            resp.raise_for_status()
            logger.info("Created branch %s from %s", branch_name, sha[:8])
            return sha

    async def commit_files(
        self, branch_name: str, files: list[GeneratedFile], message: str
    ) -> str:
        async with httpx.AsyncClient() as client:
            for f in files:
                content_b64 = b64encode(f.content.encode()).decode()

                # Check if file already exists on this branch (needed for update)
                existing_sha: str | None = None
                get_resp = await client.get(
                    f"{self._repo_url}/contents/{f.path}",
                    headers=self._headers,
                    params={"ref": branch_name},
                )
                if get_resp.status_code == 200:
                    existing_sha = get_resp.json().get("sha")

                put_body: dict = {
                    "message": message,
                    "content": content_b64,
                    "branch": branch_name,
                }
                if existing_sha:
                    put_body["sha"] = existing_sha

                resp = await client.put(
                    f"{self._repo_url}/contents/{f.path}",
                    headers=self._headers,
                    json=put_body,
                )
                resp.raise_for_status()
            logger.info("Committed %d files to %s", len(files), branch_name)
            return branch_name

    async def create_pr(
        self, branch_name: str, title: str, body: str
    ) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._repo_url}/pulls",
                headers=self._headers,
                json={
                    "title": title,
                    "body": body,
                    "head": branch_name,
                    "base": self._base,
                },
            )
            resp.raise_for_status()
            pr_url = resp.json()["html_url"]
            logger.info("Created PR: %s", pr_url)
            return pr_url
