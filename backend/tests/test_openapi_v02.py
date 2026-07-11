from app.main import create_app


HTTP_METHODS = {"get", "post", "put", "delete", "patch"}


def test_every_operation_has_summary_description_and_tags() -> None:
    schema = create_app().openapi()

    missing: list[str] = []
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            for field in ("summary", "description", "tags"):
                if not operation.get(field):
                    missing.append(f"{method.upper()} {path}: {field}")
    assert not missing, "\n".join(missing)


def test_business_routes_expose_bearer_authentication() -> None:
    schema = create_app().openapi()
    protected_prefixes = (
        "/api/agent/",
        "/api/files/",
        "/api/profiles",
        "/api/tests/",
        "/api/medicines",
        "/api/resources",
        "/api/reviews",
        "/api/learning-paths",
        "/api/learning/",
        "/api/reports",
        "/api/traces",
        "/api/metrics",
        "/api/admin",
    )

    missing: list[str] = []
    for path, path_item in schema["paths"].items():
        if not path.startswith(protected_prefixes):
            continue
        for method, operation in path_item.items():
            if method in HTTP_METHODS and not operation.get("security"):
                missing.append(f"{method.upper()} {path}")
    assert not missing, "Missing bearer security:\n" + "\n".join(missing)


def test_login_does_not_require_bearer_authentication() -> None:
    operation = create_app().openapi()["paths"]["/api/auth/login"]["post"]
    assert not operation.get("security")
