"""Integration test for BicepInfraProviderAdapter against bicep CLI."""

from __future__ import annotations

import shutil

import pytest

from src.infrastructure.adapters.bicep_adapter import BicepInfraProviderAdapter


@pytest.mark.asyncio
async def test_bicep_adapter_format_check_with_real_cli() -> None:
    if shutil.which("bicep") is None:
        pytest.skip("bicep CLI is not installed")

    adapter = BicepInfraProviderAdapter()
    files = [{"path": "main.bicep", "content": "targetScope = 'resourceGroup'\n"}]

    result = await adapter.format_check(files)
    assert result.valid is True
