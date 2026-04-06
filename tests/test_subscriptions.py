from tests.conftest import create_account


def test_subscriptions_crud(auth_client):
    account = create_account(auth_client)

    create_response = auth_client.post(
        "/subscriptions",
        json={
            "name": "Netflix",
            "amount": 15.99,
            "frequency": "monthly",
            "next_date": "2026-05-10",
            "account_id": account["id"],
            "is_active": True,
        },
    )
    assert create_response.status_code == 201, create_response.text
    subscription = create_response.json()

    list_response = auth_client.get("/subscriptions")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = auth_client.get(f"/subscriptions/{subscription['id']}")
    assert detail_response.status_code == 200

    update_response = auth_client.put(
        f"/subscriptions/{subscription['id']}",
        json={"amount": 19.99, "is_active": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["amount"] == 19.99
    assert update_response.json()["is_active"] is False

    delete_response = auth_client.delete(f"/subscriptions/{subscription['id']}")
    assert delete_response.status_code == 204
    assert auth_client.get(f"/subscriptions/{subscription['id']}").status_code == 404


def test_subscriptions_validation_rejects_unknown_account(auth_client):
    response = auth_client.post(
        "/subscriptions",
        json={
            "name": "Broken",
            "amount": 15.99,
            "frequency": "monthly",
            "next_date": "2026-05-10",
            "account_id": "missing-account",
        },
    )
    assert response.status_code == 404
