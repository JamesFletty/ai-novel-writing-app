"""API contract tests that do not call an AI provider."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import app
from core.config import settings
from db.database import Base, get_db
from models.chapter import Chapter


@pytest.fixture()
def api_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, TestingSession
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _create_story(client: TestClient, title: str = "Contract Story") -> int:
    response = client.post(
        "/api/v1/stories/",
        json={
            "title": title,
            "description": "A fixture used by contract tests.",
            "genre": "Mystery",
            "target_chapters": 4,
            "target_word_count": 8000,
        },
    )
    assert response.status_code == 200
    return response.json()["story_id"]


def test_root_and_features(api_client):
    client, _ = api_client

    root = client.get("/")
    assert root.status_code == 200
    body = root.json()
    assert body["status"] == "running"
    assert body["docs_url"] == "/docs"
    assert body["ai_provider"] == settings.ai_provider

    features = client.get("/api/v1/features")
    assert features.status_code == 200
    assert set(features.json()) == {
        "enhanced_generation",
        "multi_pass_generation",
        "quality_analysis",
        "custom_prompting",
    }


def test_openapi_operation_ids_are_unique(api_client):
    client, _ = api_client
    schema = client.get("/openapi.json")
    assert schema.status_code == 200

    operation_ids = []
    for path_item in schema.json()["paths"].values():
        for method, operation in path_item.items():
            if method.startswith("x-") or not isinstance(operation, dict):
                continue
            if "operationId" in operation:
                operation_ids.append(operation["operationId"])

    assert operation_ids
    assert len(operation_ids) == len(set(operation_ids))
    paths = schema.json()["paths"]
    assert "/api/v1/generate/providers" in paths
    assert "/api/v1/generate-enhanced/providers" in paths
    assert "/api/v1/generate-enhanced/stories/{story_id}/outline" not in paths


def test_story_crud_validation_and_delete(api_client):
    client, _ = api_client

    assert client.get("/api/v1/stories/999").status_code == 404
    assert client.delete("/api/v1/stories/999").status_code == 404

    story_id = _create_story(client)
    updated = client.put(
        f"/api/v1/stories/{story_id}",
        json={"title": "Revised Title", "genre": "Thriller"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Revised Title"
    assert updated.json()["genre"] == "Thriller"

    assert client.post("/api/v1/stories/", json={"title": ""}).status_code == 422
    assert client.put(f"/api/v1/stories/{story_id}", json={"target_chapters": 0}).status_code == 422

    deleted = client.delete(f"/api/v1/stories/{story_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/stories/{story_id}").status_code == 404


def test_character_and_world_crud(api_client):
    client, _ = api_client
    story_id = _create_story(client, "World Building")

    assert client.get("/api/v1/characters/story/999").status_code == 404
    assert client.post(
        "/api/v1/characters/story/999",
        json={"name": "Nobody"},
    ).status_code == 404

    created = client.post(
        f"/api/v1/characters/story/{story_id}",
        json={
            "name": "Mara Vale",
            "role": "protagonist",
            "motivations": "Recover the original map",
        },
    )
    assert created.status_code == 200
    character_id = created.json()["character_id"]

    renamed = client.put(
        f"/api/v1/characters/{character_id}",
        json={"name": "Mara Ell"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Mara Ell"

    listed = client.get(f"/api/v1/characters/story/{story_id}")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["Mara Ell"]

    assert client.delete(f"/api/v1/characters/{character_id}").status_code == 200
    assert client.get(f"/api/v1/characters/story/{story_id}").json() == []

    invalid_world = client.post(
        f"/api/v1/world/story/{story_id}",
        json={"type": "location", "name": "Archive", "importance": "critical"},
    )
    assert invalid_world.status_code == 422

    world = client.post(
        f"/api/v1/world/story/{story_id}",
        json={
            "type": "location",
            "name": "Glass District",
            "description": "Signs change at dawn.",
            "importance": "high",
        },
    )
    assert world.status_code == 200
    element_id = world.json()["element_id"]

    fetched = client.get(f"/api/v1/world/story/{story_id}?element_type=location")
    assert fetched.status_code == 200
    assert fetched.json()[0]["name"] == "Glass District"

    assert client.delete(f"/api/v1/world/{element_id}").status_code == 200
    assert client.get(f"/api/v1/world/story/{story_id}").json() == []

    client.post(
        f"/api/v1/characters/story/{story_id}",
        json={"name": "Ivo Vale"},
    )
    assert client.delete(f"/api/v1/stories/{story_id}").status_code == 200
    assert client.get(f"/api/v1/characters/story/{story_id}").status_code == 404


def test_missing_generation_and_export_targets(api_client):
    client, _ = api_client

    assert client.post("/api/v1/generate/stories/999/outline", json={}).status_code == 404
    assert client.post(
        "/api/v1/generate/stories/999/chapters/1",
        json={},
    ).status_code == 404
    assert client.post(
        "/api/v1/generate-enhanced/stories/999/chapters/1",
        json={"target_word_count": 1500, "quality_check": False},
    ).status_code == 404
    assert client.post(
        "/api/v1/generate-enhanced/stories/999/outline",
        json={},
    ).status_code == 404
    assert client.get("/api/v1/export/stories/999/export/preview").status_code == 404
    assert client.get("/api/v1/stories/999/chapters/1").status_code == 404


def test_quality_analysis_flags_short_cliched_prose(api_client):
    client, TestingSession = api_client
    story_id = _create_story(client, "Quality Fixture")

    assert client.post(
        f"/api/v1/generate-enhanced/stories/{story_id}/chapters/1/analyze-quality"
    ).status_code == 404

    with TestingSession() as db:
        db.add(
            Chapter(
                story_id=story_id,
                number=1,
                title="A Short Start",
                content='Little did she know. Her heart pounded. "Run," he said.',
                is_generated=False,
                is_approved=False,
                word_count=8,
            )
        )
        db.commit()

    analysis = client.post(
        f"/api/v1/generate-enhanced/stories/{story_id}/chapters/1/analyze-quality"
    )
    assert analysis.status_code == 200
    body = analysis.json()
    assert body["word_count"] < 1500
    assert any("little did" in issue.lower() for issue in body["issues"])
    assert any("heart pounded" in issue.lower() for issue in body["issues"])
    assert body["suggestions"]


def test_complexity_setting_is_shared_by_both_prefixes(api_client):
    client, _ = api_client
    original = settings.novel_complexity
    try:
        for prefix in ("/api/v1/generate", "/api/v1/generate-enhanced"):
            current = client.get(f"{prefix}/complexity")
            assert current.status_code == 200
            assert current.json()["available_levels"] == [
                "simple",
                "standard",
                "complex",
                "literary",
            ]

        updated = client.post("/api/v1/generate-enhanced/complexity/literary")
        assert updated.status_code == 200
        assert client.get("/api/v1/generate/complexity").json()["current_complexity"] == "literary"

        rejected = client.post("/api/v1/generate/complexity/purple")
        assert rejected.status_code == 400
    finally:
        settings.novel_complexity = original


def test_provider_catalog_is_local(api_client):
    client, _ = api_client
    for prefix in ("/api/v1/generate", "/api/v1/generate-enhanced"):
        response = client.get(f"{prefix}/providers")
        assert response.status_code == 200
        body = response.json()
        assert body["current_provider"] == settings.ai_provider
        assert body["available_providers"]["copilot"]["requires_api_key"] is False
        assert "openai" in body["available_providers"]
        assert "ollama" in body["available_providers"]
