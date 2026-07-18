from unittest.mock import patch
from fastapi.testclient import TestClient
from sirius_cli.preview import run_preview


def test_preview_api():
    schemas = {
        "users": [
            {"name": "id", "type": "Integer", "is_pk": True, "is_required": True},
            {"name": "username", "type": "String", "is_pk": False, "is_required": True},
            {
                "name": "phone",
                "type": "String",
                "is_pk": False,
                "is_required": False,
                "pattern": r"\+?[0-9\s\-()]{7,20}",
            },
        ],
        "posts": [
            {"name": "id", "type": "Integer", "is_pk": True, "is_required": True},
            {"name": "title", "type": "String", "is_pk": False, "is_required": True},
            {
                "name": "user_id",
                "type": "Integer",
                "is_pk": False,
                "is_required": False,
                "is_fk": True,
                "fk_target": "users.id",
            },
        ],
    }

    # Mock uvicorn.run and webbrowser.open
    with (
        patch("uvicorn.run") as mock_uvicorn_run,
        patch("webbrowser.open"),
    ):
        run_preview(schemas, port=8888)

        assert mock_uvicorn_run.called
        # Extract the FastAPI app instance from the uvicorn.run arguments
        app = mock_uvicorn_run.call_args[0][0]

        # Now we can use TestClient on the app to test all endpoints!
        client = TestClient(app)

        # Test root endpoint
        res = client.get("/")
        assert res.status_code == 200
        assert "<!DOCTYPE html>" in res.text

        # Test schema endpoint
        res = client.get("/api/schema")
        assert res.status_code == 200
        assert "users" in res.json()

        # Test get users metadata/empty list
        res = client.get("/api/users")
        assert res.status_code == 200
        assert res.json() == []

        # Test create user
        res = client.post(
            "/api/users", json={"username": "alice", "phone": "+1234567890"}
        )
        assert res.status_code == 200
        user = res.json()
        assert user["id"] == 1
        assert user["username"] == "alice"

        # Test get user
        res = client.get("/api/users/1")
        assert res.status_code == 200
        assert res.json()["username"] == "alice"

        # Test update user
        res = client.put("/api/users/1", json={"username": "alice_updated"})
        assert res.status_code == 200
        assert res.json()["username"] == "alice_updated"

        # Test delete user
        res = client.delete("/api/users/1")
        assert res.status_code == 200
        assert res.json() == {"detail": "Item deleted"}

        # Test get non-existent user (should be 404)
        res = client.get("/api/users/1")
        assert res.status_code == 404


def test_preview_with_seeding(tmp_path):
    import json

    # Create a mock JSON data file
    json_file = tmp_path / "orders.json"
    json_data = [
        {"id": 101, "item": "Laptop", "price": 999.99},
        {"id": 102, "item": "Phone", "price": 499.99},
    ]
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    schemas = {
        "orders": [
            {"name": "id", "type": "Integer", "is_pk": True, "is_required": True},
            {"name": "item", "type": "String", "is_pk": False, "is_required": True},
            {"name": "price", "type": "Float", "is_pk": False, "is_required": True},
        ]
    }

    with patch("uvicorn.run") as mock_uvicorn_run, patch("webbrowser.open"):
        run_preview(schemas, json_paths=[str(json_file)])
        app = mock_uvicorn_run.call_args[0][0]
        client = TestClient(app)

        # Query /api/orders and assert that seeded data is retrieved!
        res = client.get("/api/orders")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        assert data[0]["item"] == "Laptop"
        assert data[1]["item"] == "Phone"
