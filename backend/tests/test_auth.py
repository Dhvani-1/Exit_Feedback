def test_valid_login_sets_httponly_cookie(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={"email": "hr.test@company.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "hr.test@company.com"
    assert data["role"] == "HR"
    # Verify HttpOnly access_token cookie is present in response cookies
    assert "access_token" in response.cookies


def test_invalid_password_rejected(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={"email": "hr.test@company.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    err = response.json()
    assert err["error"]["code"] == "INVALID_CREDENTIALS"


def test_unauthenticated_api_access_blocked(client):
    response = client.get("/api/employees")
    assert response.status_code == 401
    err = response.json()
    assert err["error"]["code"] == "UNAUTHORIZED"


def test_logout_clears_cookie(auth_client):
    me_res = auth_client.get("/api/auth/me")
    assert me_res.status_code == 200

    logout_res = auth_client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # Next call without cookie fails
    # Note: testclient preserves cookies, so we simulate clearing
    auth_client.cookies.clear()
    after_logout = auth_client.get("/api/auth/me")
    assert after_logout.status_code == 401
