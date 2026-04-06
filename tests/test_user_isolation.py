from tests.conftest import create_account


def test_user_cannot_access_other_users_transactions(auth_client, second_auth_client):
    owner_account = create_account(auth_client, "Owner account")
    create_tx_response = auth_client.post(
        "/transactions",
        json={
            "account_id": owner_account["id"],
            "date": "2026-04-01",
            "amount": -42.0,
            "description": "Private transaction",
            "category": "Autres",
        },
    )
    assert create_tx_response.status_code == 201
    transaction_id = create_tx_response.json()["id"]

    second_account = create_account(second_auth_client, "Second account")

    assert second_auth_client.get(f"/transactions/{transaction_id}").status_code == 404
    assert second_auth_client.put(
        f"/transactions/{transaction_id}",
        json={"description": "Hacked"},
    ).status_code == 404
    assert second_auth_client.delete(f"/transactions/{transaction_id}").status_code == 404

    cross_account_create = second_auth_client.post(
        "/transactions",
        json={
            "account_id": owner_account["id"],
            "date": "2026-04-02",
            "amount": -10.0,
            "description": "Cross-account write attempt",
            "category": "Autres",
        },
    )
    assert cross_account_create.status_code == 404

    second_user_tx = second_auth_client.post(
        "/transactions",
        json={
            "account_id": second_account["id"],
            "date": "2026-04-03",
            "amount": -5.0,
            "description": "Second user transaction",
            "category": "Autres",
        },
    )
    assert second_user_tx.status_code == 201

    owner_ids = {item["id"] for item in auth_client.get("/transactions").json()}
    second_ids = {item["id"] for item in second_auth_client.get("/transactions").json()}
    assert transaction_id in owner_ids
    assert transaction_id not in second_ids
    assert second_user_tx.json()["id"] not in owner_ids


def test_user_cannot_access_other_users_accounts_subscriptions_or_categories(auth_client, second_auth_client):
    owner_account = create_account(auth_client, "Owner account")
    owner_category = auth_client.post(
        "/categories",
        json={"name": "Secret", "color": "#111111"},
    ).json()
    owner_subscription = auth_client.post(
        "/subscriptions",
        json={
            "name": "Private sub",
            "amount": 9.99,
            "frequency": "monthly",
            "next_date": "2026-05-01",
            "account_id": owner_account["id"],
        },
    ).json()

    assert second_auth_client.get(f"/accounts/{owner_account['id']}").status_code == 404
    assert second_auth_client.put(
        f"/accounts/{owner_account['id']}",
        json={"name": "Nope"},
    ).status_code == 404
    assert second_auth_client.delete(f"/accounts/{owner_account['id']}").status_code == 404

    assert second_auth_client.get(f"/categories/{owner_category['id']}").status_code == 404
    assert second_auth_client.put(
        f"/categories/{owner_category['id']}",
        json={"name": "Nope"},
    ).status_code == 404
    assert second_auth_client.delete(f"/categories/{owner_category['id']}").status_code == 404

    assert second_auth_client.get(f"/subscriptions/{owner_subscription['id']}").status_code == 404
    assert second_auth_client.put(
        f"/subscriptions/{owner_subscription['id']}",
        json={"name": "Nope"},
    ).status_code == 404
    assert second_auth_client.delete(f"/subscriptions/{owner_subscription['id']}").status_code == 404

    assert owner_account["id"] not in {item["id"] for item in second_auth_client.get("/accounts").json()}
    assert owner_category["id"] not in {item["id"] for item in second_auth_client.get("/categories").json()}
    assert owner_subscription["id"] not in {item["id"] for item in second_auth_client.get("/subscriptions").json()}
