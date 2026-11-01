def create(client, headers, **fields):
    data = {"title": "VPN setup", "body": "Install the client.", **fields}
    response = client.post("/api/articles", json=data, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_create_starts_as_draft_version_1(client, alice):
    article = create(client, alice)
    assert article["status"] == "draft"
    assert article["current_version"] == 1
    assert article["number"] == "KB0001001"


def test_edit_creates_a_version_only_when_content_changes(client, alice):
    article = create(client, alice)
    url = f"/api/articles/{article['id']}"

    edited = client.patch(url, json={"body": "Install the new client."}, headers=alice).json()
    assert edited["current_version"] == 2

    same_again = client.patch(url, json={"body": "Install the new client."}, headers=alice).json()
    assert same_again["current_version"] == 2

    visibility_only = client.patch(url, json={"visibility": "private"}, headers=alice).json()
    assert visibility_only["current_version"] == 2
    assert visibility_only["visibility"] == "private"

    versions = client.get(f"{url}/versions", headers=alice).json()
    assert [v["version"] for v in versions] == [2, 1]
    old = client.get(f"{url}/versions/1", headers=alice).json()
    assert old["body"] == "Install the client."


def test_lifecycle(client, alice):
    url = f"/api/articles/{create(client, alice)['id']}"

    assert client.post(f"{url}/retire", headers=alice).status_code == 409  # draft can't be retired
    published = client.post(f"{url}/publish", headers=alice).json()
    assert published["status"] == "published"
    assert published["published_at"] is not None
    assert client.post(f"{url}/publish", headers=alice).status_code == 409

    assert client.post(f"{url}/retire", headers=alice).json()["status"] == "retired"
    assert client.patch(url, json={"title": "New"}, headers=alice).status_code == 409
    assert client.post(f"{url}/restore", headers=alice).json()["status"] == "draft"


def test_only_drafts_can_be_deleted(client, alice):
    url = f"/api/articles/{create(client, alice)['id']}"
    client.post(f"{url}/publish", headers=alice)
    assert client.delete(url, headers=alice).status_code == 409

    draft_url = f"/api/articles/{create(client, alice)['id']}"
    assert client.delete(draft_url, headers=alice).status_code == 204
    assert client.get(draft_url, headers=alice).status_code == 404


def test_permissions(client, alice, bob):
    private = create(client, alice, visibility="private")
    draft = create(client, alice)
    published = create(client, alice)
    client.post(f"/api/articles/{published['id']}/publish", headers=alice)

    # Bob can't see Alice's drafts or private articles: 404, not 403.
    assert client.get(f"/api/articles/{private['id']}", headers=bob).status_code == 404
    assert client.get(f"/api/articles/{draft['id']}", headers=bob).status_code == 404

    # Bob can read her published public article, but not change it.
    assert client.get(f"/api/articles/{published['id']}", headers=bob).status_code == 200
    assert client.patch(f"/api/articles/{published['id']}", json={"title": "Hacked"}, headers=bob).status_code == 403

    bobs_list = client.get("/api/articles", headers=bob).json()
    assert [a["id"] for a in bobs_list["items"]] == [published["id"]]
    assert bobs_list["total"] == 1


def test_list_filters_and_search(client, alice):
    create(client, alice, title="Reset your password", category="Accounts")
    create(client, alice, title="VPN error 809", body="Error 809 means UDP 500 is blocked.", category="Network")

    assert client.get("/api/articles", params={"q": "809"}, headers=alice).json()["total"] == 1
    assert client.get("/api/articles", params={"q": "kb0001001"}, headers=alice).json()["total"] == 1
    assert client.get("/api/articles", params={"category": "Accounts"}, headers=alice).json()["total"] == 1
    assert client.get("/api/articles", params={"status": "published"}, headers=alice).json()["total"] == 0

    page = client.get("/api/articles", params={"limit": 1}, headers=alice).json()
    assert len(page["items"]) == 1
    assert page["total"] == 2

    categories = client.get("/api/categories", headers=alice).json()
    assert categories == [{"category": "Accounts", "count": 1}, {"category": "Network", "count": 1}]
