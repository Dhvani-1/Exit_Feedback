def test_optimistic_locking_stale_update_rejected(auth_client):
    # 1. Create employee (initial version = 1)
    create_payload = {
        "full_name": "Original Name",
        "personal_email": "concurrency@company.com",
        "last_working_date": "2026-04-15",
    }
    res_create = auth_client.post("/api/employees", json=create_payload)
    assert res_create.status_code == 201
    emp = res_create.json()
    emp_id = emp["id"]
    initial_version = emp["version"]
    assert initial_version == 1

    # 2. User B updates the employee record first (version increments to 2)
    update_user_b = {
        "full_name": "Name Updated By User B",
        "personal_email": "concurrency@company.com",
        "last_working_date": "2026-04-15",
        "version": initial_version,  # version = 1
    }
    res_user_b = auth_client.put(f"/api/employees/{emp_id}", json=update_user_b)
    assert res_user_b.status_code == 200
    assert res_user_b.json()["version"] == 2

    # 3. User A attempts to update using stale version = 1 (which was fetched before User B updated)
    update_user_a = {
        "full_name": "Name Updated By User A (Stale)",
        "personal_email": "concurrency@company.com",
        "last_working_date": "2026-04-15",
        "version": initial_version,  # version = 1 (STALE!)
    }
    res_user_a = auth_client.put(f"/api/employees/{emp_id}", json=update_user_a)
    assert res_user_a.status_code == 409
    err = res_user_a.json()
    assert err["error"]["code"] == "STALE_EMPLOYEE_RECORD"
    assert "updated by another user" in err["error"]["message"]
