# Contributing

## Getting Started

1. Clone the repo and create your `.env` file:
   ```bash
   git clone <repo-url>
   cd <project-name>
   cp .env.example .env
   ```
2. Install dependencies:
   ```bash
   # Frontend
   cd frontend
   npm install

   # Backend
   cd ../backend
   pip install -r requirements.txt
   ```
3. Run the project:
   ```bash
   # Frontend
   npm run dev

   # Backend
   python main.py
   ```

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

- **Python**: Follow PEP 8. Use type hints. Format with `black`.
- **TypeScript/React**: Use functional components and hooks. No `any` types. Format with `prettier`.
- **Agent SDK**: Keep agent configs in dedicated files under `/agents`. Document any new tools or skills added.

## Do Before Pushing

- [ ] Code runs locally without errors
- [ ] No secrets or `.env` values committed
- [ ] New dependencies added to `requirements.txt` or `package.json`
- [ ] README updated if setup steps changed
