---
description: "Deploy InfraAgent backend to Azure AI Foundry as a hosted agent."
---

# Deploy to Foundry

Deploy the InfraAgent backend to Azure AI Foundry Agent Service.

## Pre-Flight Checks

1. Verify `backend/main.py` runs locally without startup errors
2. Verify `pyproject.toml` has all dependencies
3. Verify `.env` has `PROJECT_ENDPOINT` configured
4. Verify Docker Desktop is running

## Deployment Steps

1. **Build Docker image**:
   ```bash
   cd backend
   docker build -t infraagent-backend:latest .
   ```

2. **Test locally**:
   ```bash
   docker run -p 8000:8000 --env-file ../.env infraagent-backend:latest
   curl http://localhost:8000/health
   ```

3. **Push to ACR**:
   ```bash
   az acr login --name <acr-name>
   docker tag infraagent-backend:latest <acr-name>.azurecr.io/infraagent-backend:latest
   docker push <acr-name>.azurecr.io/infraagent-backend:latest
   ```

4. **Deploy to Foundry**: Run VS Code command `Microsoft Foundry: Deploy Hosted Agent` from the Command Palette

## Post-Deploy Verification

- Check agent appears in AI Toolkit → My Resources → Recent Agents
- Test with Agent Inspector
- Verify MCP server connectivity (remote HTTP endpoints)
