import os
from sirius_cli.generator import generate_project


def test_generate_project(tmp_project_dir):
    # Mock schema matching the format output by the parser
    mock_schema = {
        "users": [
            {"name": "id", "type": "Integer", "is_pk": True},
            {"name": "name", "type": "String", "is_pk": False},
            {"name": "is_active", "type": "Boolean", "is_pk": False},
        ],
        "posts": [
            {"name": "id", "type": "Integer", "is_pk": True},
            {"name": "title", "type": "String", "is_pk": False},
            {
                "name": "user_id",
                "type": "Integer",
                "is_pk": False,
                "foreign_key": "users.id",
            },
        ],
    }

    project_name = "test_app"
    out_dir = os.path.join(tmp_project_dir, project_name)

    generate_project(
        project_path=out_dir,
        schemas=mock_schema,
        project_name=project_name,
        theme="blue",
        port=8000,
        api_url="http://localhost:8000",
        db_type="sqlite",
        auth=False,
    )

    # Check directory structure
    assert os.path.isdir(out_dir)
    assert os.path.isdir(os.path.join(out_dir, "backend"))
    assert os.path.isdir(os.path.join(out_dir, "frontend"))

    # Check backend files
    assert os.path.isfile(os.path.join(out_dir, "backend", "main.py"))
    assert os.path.isfile(os.path.join(out_dir, "backend", "database.py"))
    assert os.path.isfile(os.path.join(out_dir, "backend", "models.py"))
    assert os.path.isfile(os.path.join(out_dir, "backend", "schemas.py"))

    # Check frontend files
    assert os.path.isfile(os.path.join(out_dir, "frontend", "package.json"))
    assert os.path.isfile(os.path.join(out_dir, "frontend", "src", "App.tsx"))

    # Verify Jinja2 template rendering output content
    with open(os.path.join(out_dir, "backend", "models.py"), "r") as f:
        models_content = f.read()
        assert "class UsersModel(Base):" in models_content
        assert "class PostsModel(Base):" in models_content
        assert "ForeignKey('users.id')" in models_content
