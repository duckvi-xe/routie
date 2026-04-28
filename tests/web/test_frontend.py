"""Tests for the frontend static file serving."""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient, ASGITransport

from routie.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestFrontendServing:
    """Tests that static frontend files are served correctly."""

    async def test_index_html_served_at_root(self, client: AsyncClient):
        """GET / should return the frontend HTML page."""
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    async def test_index_html_contains_svelte_app(self, client: AsyncClient):
        """The HTML should be the Svelte-built frontend."""
        resp = await client.get("/")
        assert resp.status_code == 200
        body = resp.text
        # Svelte-built index.html has a div#app
        assert "app" in body
        # Vite injects a module script tag
        assert ".js" in body
        assert ".css" in body

    async def test_vite_assets_are_served(self, client: AsyncClient):
        """Vite built JS and CSS bundles should be accessible from backend."""
        resp = await client.get("/")
        body = resp.text

        # Find all asset references (JS and CSS) that are relative paths (not CDN)
        css_links = re.findall(r'href=["\'](/[^"\']+\.css[^"\']*)["\']', body)
        js_links = re.findall(r'src=["\'](/[^"\']+\.js[^"\']*)["\']', body)

        all_assets = css_links + js_links
        assert len(all_assets) > 0, "No local assets found in index.html"

        for asset in all_assets:
            asset_resp = await client.get(asset)
            assert asset_resp.status_code == 200, f"Asset {asset} not found (status {asset_resp.status_code})"

    async def test_api_still_works_with_frontend_mounted(self, client: AsyncClient):
        """API endpoints should still respond correctly."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_post_profile_via_api(self, client: AsyncClient):
        """Profile creation should still work with the frontend mounted."""
        resp = await client.post(
            "/api/v1/profiles",
            json={
                "name": "FrontendTest",
                "activity_type": "running",
                "skill_level": "intermediate",
            },
        )
        assert resp.status_code == 201

    async def test_frontend_route_creation_flow(self, client: AsyncClient):
        """Full flow: create profile → plan route → get route."""
        # Create profile
        profile_resp = await client.post(
            "/api/v1/profiles",
            json={"name": "Test", "activity_type": "running", "skill_level": "beginner"},
        )
        assert profile_resp.status_code == 201
        profile_id = profile_resp.json()["id"]

        # Plan route
        route_resp = await client.post(
            "/api/v1/routes/plan",
            json={
                "profile_id": profile_id,
                "activity_type": "running",
                "max_distance_km": 5.0,
                "terrain_type": "flat",
            },
        )
        assert route_resp.status_code == 201
        data = route_resp.json()
        assert data["distance_km"] <= 5.0
        assert data["activity_type"] == "running"
        assert len(data["waypoints"]) > 0

        # Get route by ID
        route_id = data["id"]
        get_resp = await client.get(f"/api/v1/routes/{route_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == route_id
