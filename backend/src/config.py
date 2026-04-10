import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Settings:
    # Azure AI Foundry
    project_endpoint: str = os.getenv("PROJECT_ENDPOINT", "")
    model_deployment: str = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4o")

    # Azure
    subscription_id: str = os.getenv("AZURE_SUBSCRIPTION_ID", "")
    tenant_id: str = os.getenv("AZURE_TENANT_ID", "")

    # GitHub
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    github_repo_owner: str = os.getenv("GITHUB_REPO_OWNER", "")
    github_repo_name: str = os.getenv("GITHUB_REPO_NAME", "")
    github_target_branch: str = os.getenv("GITHUB_TARGET_BRANCH", "main")

    # MCP Servers (optional — leave blank to skip tool grounding)
    mcp_bicep_url: str = os.getenv("MCP_BICEP_URL", "")
    mcp_terraform_url: str = os.getenv("MCP_TERRAFORM_URL", "")
    mcp_azure_url: str = os.getenv("MCP_AZURE_URL", "")

    # Deploy
    deploy_resource_group: str = os.getenv("DEPLOY_RESOURCE_GROUP", "")
    deploy_location: str = os.getenv("DEPLOY_LOCATION", "westeurope")

    # App
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    cors_origins: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")


settings = Settings()
