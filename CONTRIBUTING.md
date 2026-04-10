# Contributing

## Getting Started

1. Clone the repo and create your `.env` file:
   ```bash
   git clone <repo-url>
   cd "Terraformers Anonymous"
   cp .env.example .env
   ```
2. Install dependencies:
   ```bash
   cd backend
   uv sync --extra dev
   ```
3. Authenticate with Azure:
   ```bash
   az login
   ```
4. Run the backend:
   ```bash
   cd backend
   uv run uvicorn main:app --reload --port 8000
   ```

See [docs/setup.md](docs/setup.md) for full setup including MCP servers and AI Toolkit.

## Branch Naming

Create a branch from `main` for every task:

| Prefix       | Use for                  |
|--------------|--------------------------|
| `feature/`   | New functionality        |
| `fix/`       | Bug fixes                |
| `chore/`     | Config, dependencies, CI |

Example: `feature/agent-chat-ui`, `fix/api-auth-error`

## Commit Messages

Keep them short and descriptive in imperative mood:

```
feat: add agent response streaming
fix: resolve token refresh loop
chore: update Next.js to 15
```

## Pull Request Process

1. Create your branch: `git checkout -b feature/your-task`
2. Make your changes and commit often.
3. Push and open a PR against `main`.
4. At least **1 teammate must review and approve** before merging.
5. Resolve all review comments before merging.
6. Use **Squash and Merge** to keep `main` history clean.

## Code Guidelines

- **Python**: Python 3.11+, `from __future__ import annotations`, type hints, format with **Ruff**
- **TypeScript/React**: Use functional components and hooks. No `any` types. Format with `prettier`.
- **Agents**: System prompts in `backend/src/agents/prompts/`, adapters implement ports from `core/ports.py`. See [docs/agents.md](docs/agents.md).
- **IaC**: Bicep-first, AVM modules, required tags. See [docs/architecture.md](docs/architecture.md).

## Adding Dependencies

```bash
cd backend
uv add <package-name>           # runtime dependency
uv add --dev <package-name>     # dev-only dependency
```

Never edit `pyproject.toml` dependency lists by hand — use `uv add`.

## MCP Servers

MCP servers are configured in `.vscode/mcp.json`. See [docs/mcp-servers.md](docs/mcp-servers.md) for setup instructions.

## Copilot Custom Agent

The project includes a custom `@InfraAgent Dev` workspace agent (`.github/agents/infraagent-dev.agent.md`) and reusable prompt files (`.github/prompts/`). Type `@` in Copilot Chat to use the agent, or open the Command Palette and search "Run Prompt" for the prompt files.

## Do Before Pushing

- [ ] Code runs locally without errors
- [ ] No secrets or `.env` values committed
- [ ] New dependencies added via `uv add` (reflected in `pyproject.toml`)
- [ ] Ruff passes: `uv run ruff check . && uv run ruff format --check .`
- [ ] README or docs updated if setup steps changed
