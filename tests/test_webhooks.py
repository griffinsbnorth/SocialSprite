import json
import pytest
import hmac
import hashlib
import os

from website.models import Post


def test_patreon_webhook(authenticated_client):
    from dotenv import load_dotenv
    load_dotenv()

    patreon_data = {
        "data": {
            "type": "post",
            "id": '1',
            "attributes": {
                "title": "Patreon webhook test",
                "content": "test webhook content",
                "url": "/test_url",
                "published_at": "You literally never use this"
                }

            }
        }
    payload_bytes = json.dumps(patreon_data).encode("utf-8")

    webhook_secret = os.getenv("PATREON_WEBHOOK_SECRET")
    expected_sig = hmac.new(
        webhook_secret.encode('utf-8'),
        payload_bytes,
        hashlib.md5
    ).hexdigest()

    headers = {
        "X-Patreon-Signature": expected_sig
    }

    response = authenticated_client.post('/patreonpost', data=payload_bytes, content_type="application/json", headers=headers, follow_redirects=True)
    assert response.status_code == 200

    # Check if it added to the database properly
    patreon_post = Post.query.filter(Post.title == patreon_data["data"]["attributes"]["title"]).first()
    assert patreon_post != None