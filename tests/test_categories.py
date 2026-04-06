def test_categories_crud(auth_client):
    create_response = auth_client.post(
        "/categories",
        json={"name": "Work", "color": "#ff0000"},
    )
    assert create_response.status_code == 201
    category = create_response.json()

    list_response = auth_client.get("/categories")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = auth_client.get(f"/categories/{category['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "Work"

    update_response = auth_client.put(
        f"/categories/{category['id']}",
        json={"name": "Work Updated", "color": "#00ff00"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Work Updated"

    delete_response = auth_client.delete(f"/categories/{category['id']}")
    assert delete_response.status_code == 204
    assert auth_client.get(f"/categories/{category['id']}").status_code == 404


def test_categories_validation_rejects_missing_required_field(auth_client):
    response = auth_client.post("/categories", json={"color": "#123456"})
    assert response.status_code == 422
