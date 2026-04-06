def test_bank_accounts_crud(auth_client):
    create_response = auth_client.post(
        "/accounts",
        json={
            "name": "Daily account",
            "type": "personal",
            "balance": 2500.0,
            "currency": "EUR",
        },
    )
    assert create_response.status_code == 201
    account = create_response.json()

    list_response = auth_client.get("/accounts")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = auth_client.get(f"/accounts/{account['id']}")
    assert detail_response.status_code == 200

    update_response = auth_client.put(
        f"/accounts/{account['id']}",
        json={"name": "Emergency fund", "balance": 3200.0},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Emergency fund"
    assert update_response.json()["balance"] == 3200.0

    delete_response = auth_client.delete(f"/accounts/{account['id']}")
    assert delete_response.status_code == 204
    assert auth_client.get(f"/accounts/{account['id']}").status_code == 404


def test_bank_accounts_validation_rejects_missing_name(auth_client):
    response = auth_client.post(
        "/accounts",
        json={"type": "personal", "balance": 10.0, "currency": "EUR"},
    )
    assert response.status_code == 422
