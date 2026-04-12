"""Source Control port interface.

Contract between the application layer and version control systems (GitHub, Azure DevOps, etc.).
Ref: TechSpec Section 2.1, lines 244-266
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PRResult:
    """Result of creating a pull request.

    Fields:
        number: PR number/ID
        url: API URL for the PR
        html_url: Web URL for the PR
        state: PR state (open, closed, etc.)
        branch_name: Source branch name
    """
    number: int
    url: str
    html_url: str
    state: str
    branch_name: str


@dataclass
class PipelineStatus:
    """Status of a CI/CD pipeline run.

    Fields:
        status: "queued" | "in_progress" | "completed" | "failed"
        conclusion: "success" | "failure" | "cancelled" (null if in progress)
        plan_output: Output from the plan job (if available)
        run_url: URL to view the run
    """
    status: str  # "queued" | "in_progress" | "completed" | "failed"
    conclusion: str | None  # "success" | "failure" | "cancelled"
    plan_output: str | None = None
    run_url: str | None = None


class ISourceControlPort(ABC):
    """Abstracts over version control systems (GitHub, Azure DevOps, etc.).

    Manages branches, commits, PRs, and workflow triggers.
    """

    @abstractmethod
    async def create_branch(self, repo: str, branch: str, base: str) -> str:
        """Create a new branch.

        Args:
            repo: Repository name or URL
            branch: New branch name
            base: Base branch to branch from

        Returns:
            Created branch name
        """
        ...

    @abstractmethod
    async def commit_files(
        self, repo: str, branch: str, files: list[dict], message: str
    ) -> str:
        """Commit files to a branch.

        Args:
            repo: Repository name or URL
            branch: Target branch
            files: List of {"path": "...", "content": "..."} dicts
            message: Commit message

        Returns:
            Commit SHA
        """
        ...

    @abstractmethod
    async def create_pr(
        self, repo: str, title: str, body: str, head: str, base: str
    ) -> PRResult:
        """Create a pull request.

        Args:
            repo: Repository name or URL
            title: PR title
            body: PR description
            head: Source branch name
            base: Target branch name

        Returns:
            PRResult with PR details
        """
        ...

    @abstractmethod
    async def get_pipeline_status(self, repo: str, run_id: int) -> PipelineStatus:
        """Get status of a CI/CD pipeline run.

        Args:
            repo: Repository name or URL
            run_id: Run ID from CI/CD system

        Returns:
            PipelineStatus with current run state
        """
        ...

    @abstractmethod
    async def trigger_workflow(
        self, repo: str, workflow: str, ref: str, inputs: dict
    ) -> int:
        """Trigger a CI/CD workflow run.

        Args:
            repo: Repository name or URL
            workflow: Workflow name or file
            ref: Branch/tag/SHA to run on
            inputs: Workflow input parameters

        Returns:
            Run ID for later status checks
        """
        ...
