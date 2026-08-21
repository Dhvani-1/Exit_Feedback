from datetime import date


def test_create_employee_success(auth_client):
    payload = {
        "full_name": "Alice Smith",
        "personal_email": "alice.smith@gmail.com",
        "last_working_date": "2026-01-31",
    }
    response = auth_client.post("/api/employees", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["full_name"] == "Alice Smith"
    assert data["personal_email"] == "alice.smith@gmail.com"
    assert data["last_working_date"] == "2026-01-31"
    # Backend must calculate 3 calendar months later (31 Jan -> 30 Apr)
    assert data["feedback_due_date"] == "2026-04-30"
    assert data["status"] == "SCHEDULED"
    assert data["version"] == 1


def test_active_email_duplicate_vs_rehire_cancelled(auth_client):
    payload1 = {
        "full_name": "Charlie Brown",
        "personal_email": "charlie@gmail.com",
        "last_working_date": "2026-03-10",
    }
    res1 = auth_client.post("/api/employees", json=payload1)
    assert res1.status_code == 201

    # Attempt creation of active employee with same personal_email + LWD -> Rejected
    res2 = auth_client.post("/api/employees", json=payload1)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "ACTIVE_EMPLOYEE_EXISTS_WITH_EMAIL"

    # Cancel first record (soft cancel)
    emp_id = res1.json()["id"]
    cancel_res = auth_client.post(f"/api/employees/{emp_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Re-hire scenario with new LWD: Now creating new employee record with same personal email succeeds!
    payload2 = {
        "full_name": "Charlie Brown",
        "personal_email": "charlie@gmail.com",
        "last_working_date": "2027-08-15",
    }
    res3 = auth_client.post("/api/employees", json=payload2)
    assert res3.status_code == 201
    assert res3.json()["last_working_date"] == "2027-08-15"


def test_pagination_max_page_size_safety(auth_client):
    response = auth_client.get("/api/employees?page_size=200")
    # Pydantic Query max 100 validation returns 422
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_search_and_filter_employees(auth_client):
    emp1 = {
        "full_name": "Developer Alpha",
        "personal_email": "alpha@tech.com",
        "last_working_date": "2026-06-01",
    }
    emp2 = {
        "full_name": "Marketer Beta",
        "personal_email": "beta@marketing.com",
        "last_working_date": "2026-07-01",
    }
    auth_client.post("/api/employees", json=emp1)
    auth_client.post("/api/employees", json=emp2)

    # Search by name
    res_search = auth_client.get("/api/employees?search=Alpha")
    assert res_search.status_code == 200
    data = res_search.json()
    assert data["total"] == 1
    assert data["items"][0]["full_name"] == "Developer Alpha"


def test_update_employee_recalculates_due_date(auth_client):
    emp_create = {
        "full_name": "Update User",
        "personal_email": "update.user@gmail.com",
        "last_working_date": "2026-01-15",
    }
    create_res = auth_client.post("/api/employees", json=emp_create)
    assert create_res.status_code == 201
    created_data = create_res.json()
    emp_db_id = created_data["id"]
    assert created_data["feedback_due_date"] == "2026-04-15"

    # Update last_working_date to 30 Nov 2026
    update_payload = {
        "full_name": "Update User Modified",
        "personal_email": "update.user@gmail.com",
        "last_working_date": "2026-11-30",
        "version": created_data["version"],
    }
    update_res = auth_client.put(f"/api/employees/{emp_db_id}", json=update_payload)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["full_name"] == "Update User Modified"
    assert updated_data["last_working_date"] == "2026-11-30"
    # Backend must automatically recalculate 30 Nov 2026 -> 28 Feb 2027
    assert updated_data["feedback_due_date"] == "2027-02-28"
    assert updated_data["version"] == 2
