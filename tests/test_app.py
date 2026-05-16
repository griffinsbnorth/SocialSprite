import pytest

def test_home(authenticated_client):
    """Test the home route."""
    response = authenticated_client.get('/')
    assert response.status_code == 200

def test_non_existent_route(client):
    """Test for a non-existent route."""
    response = client.get('/non-existent')
    assert response.status_code == 404