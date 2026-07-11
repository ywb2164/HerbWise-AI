"""HTTP smoke test for the V0.2 demo workflow.

Run after migration and two idempotent seed passes. It exits non-zero on the
first failed assertion so it can be used in local CI.
"""

import os
import sys
import time

import httpx

BASE_URL = os.getenv("HERBWISE_BASE_URL", "http://localhost:8000").rstrip("/")


def request(client: httpx.Client, method: str, path: str, **kwargs) -> dict:
    response = client.request(method, f"{BASE_URL}{path}", timeout=10, **kwargs)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("code") == 0:
        return payload["data"]
    return payload


def login(client: httpx.Client, username: str) -> dict:
    return request(
        client,
        "POST",
        "/api/auth/login",
        json={"username": username, "password": "HerbWise@2026"},
    )


def main() -> int:
    with httpx.Client() as client:
        admin = login(client, "admin")
        student = login(client, "student")
        headers = {"Authorization": f"Bearer {admin['access_token']}"}
        request(client, "GET", "/api/auth/me", headers=headers)
        request(client, "GET", "/api/auth/menus", headers=headers)
        request(client, "GET", "/api/profiles/stu_001", headers=headers)
        request(client, "GET", "/api/profiles/stu_001/dimensions", headers=headers)
        request(client, "GET", "/api/medicines/by-name/黄耆", headers=headers)
        request(client, "GET", "/api/medicines/by-name/Astragalus", headers=headers)
        request(client, "GET", "/api/medicines/by-name/黄芪", headers=headers)
        resource = request(
            client,
            "POST",
            "/api/resources/generate",
            headers=headers,
            json={
                "learner_id": "stu_001",
                "medicine_name": "黄芪",
                "resource_type": "lecture",
                "difficulty": "basic",
                "task_id": None,
            },
        )
        request(
            client,
            "POST",
            "/api/reviews/check",
            headers=headers,
            params={"resource_id": resource["resource_id"]},
        )
        request(
            client,
            "POST",
            "/api/learning-paths/update",
            headers=headers,
            params={"learner_id": "stu_001"},
        )
        task = request(
            client,
            "POST",
            "/api/agent/tasks",
            headers=headers,
            json={
                "learner_id": "stu_001",
                "task_type": "full_loop",
                "image_id": "img_smoke",
            },
        )
        for _ in range(25):
            current = request(
                client, "GET", f"/api/agent/tasks/{task['task_id']}", headers=headers
            )
            if current["status"] == "success":
                break
            if current["status"] == "failed":
                raise RuntimeError(current.get("error_message") or "workflow failed")
            time.sleep(0.2)
        else:
            raise RuntimeError("workflow did not finish within five seconds")
        request(
            client, "GET", f"/api/agent/tasks/{task['task_id']}/events", headers=headers
        )
        request(
            client, "GET", f"/api/agent/tasks/{task['task_id']}/logs", headers=headers
        )
        request(
            client, "GET", f"/api/traces/by-task/{task['task_id']}", headers=headers
        )
        request(client, "GET", "/api/metrics/overview", headers=headers)
        assert student["user"]["username"] == "student"
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"smoke_v02 failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
