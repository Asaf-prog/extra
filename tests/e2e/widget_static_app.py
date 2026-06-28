"""Static app used by Playwright widget smoke tests."""

from __future__ import annotations

from fastapi import FastAPI

from agent_manager.api.web import mount_web
from agent_manager.config import Settings

app = FastAPI()
mount_web(app, Settings())
