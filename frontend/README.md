# InfraAgent Frontend

## Development Setup

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment Variables

```bash
# Optional — defaults to http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Next.js rewrites `/api/*` to the FastAPI backend, so no CORS config needed in dev.

## Pages

| Route | Description |
|---|---|
| `/` | Chat with Consulting Agent, trigger pipeline |
| `/pipeline/[sessionId]` | Live pipeline status, file viewer, H1/H2 approval gates |

## Stack

- **Next.js 15** (App Router, Turbopack)
- **TypeScript** + **Tailwind CSS**
- **Auto-polling** pipeline status every 3s until terminal stage
