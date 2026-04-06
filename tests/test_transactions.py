from tests.conftest import create_account


def test_transactions_crud_and_pagination(auth_client):
    account = create_account(auth_client)

    created_ids = []
    for day in range(1, 4):
        response = auth_client.post(
            "/transactions",
            json={
                "account_id": account["id"],
                "date": f"2026-04-0{day}",
                "amount": -10.0 * day,
                "description": f"Expense {day}",
                "category": "Autres",
                "is_recurring": False,
            },
        )
        assert response.status_code == 201, response.text
        created_ids.append(response.json()["id"])

    list_response = auth_client.get("/transactions")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 3

    paginated_response = auth_client.get("/transactions", params={"limit": 2, "offset": 1})
    assert paginated_response.status_code == 200
    assert len(paginated_response.json()) == 2

    detail_response = auth_client.get(f"/transactions/{created_ids[0]}")
    assert detail_response.status_code == 200

    update_response = auth_client.put(
        f"/transactions/{created_ids[0]}",
        json={"description": "Updated expense", "amount": -99.5},
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Updated expense"
    assert update_response.json()["amount"] == -99.5

    delete_response = auth_client.delete(f"/transactions/{created_ids[1]}")
    assert delete_response.status_code == 204

    final_list_response = auth_client.get("/transactions")
    remaining_ids = {item["id"] for item in final_list_response.json()}
    assert created_ids[1] not in remaining_ids
    assert len(remaining_ids) == 2


def test_transactions_validation_rejects_bad_payload(auth_client):
    response = auth_client.post(
        "/transactions",
        json={
            "account_id": "missing-account",
            "date": "2026-04-01",
            "amount": -12.0,
            "description": "No account",
            "category": "Autres",
        },
    )
    assert response.status_code == 404

    invalid_query_response = auth_client.get("/transactions", params={"limit": 0})
    assert invalid_query_response.status_code == 422
