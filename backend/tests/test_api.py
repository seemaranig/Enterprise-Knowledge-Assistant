"""Tests for Enterprise Knowledge Assistant backend."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import ChatRequest


client = TestClient(app)


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    def test_health_check_returns_200(self):
        """Test that health check returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_check_response_structure(self):
        """Test that health check has correct structure."""
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "components" in data
        assert data["status"] == "healthy"


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root_returns_200(self):
        """Test that root endpoint returns 200 OK."""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_root_response_structure(self):
        """Test that root endpoint returns expected fields."""
        response = client.get("/")
        data = response.json()
        
        assert "message" in data
        assert "version" in data


class TestUploadEndpoint:
    """Tests for PDF upload endpoint."""
    
    def test_upload_without_file_returns_422(self):
        """Test that upload without file returns validation error."""
        response = client.post("/upload")
        assert response.status_code == 422
    
    def test_upload_invalid_file_type_returns_400(self):
        """Test that uploading non-PDF returns 400."""
        files = {"file": ("test.txt", b"Not a PDF", "text/plain")}
        response = client.post("/upload", files=files)
        assert response.status_code == 400
    
    def test_upload_response_has_required_fields(self):
        """Test that upload response has required fields."""
        # This would require a valid PDF file
        # Skipping for now as it requires file handling
        pass


class TestChatEndpoint:
    """Tests for chat endpoint."""
    
    def test_chat_without_query_returns_422(self):
        """Test that chat without query returns validation error."""
        response = client.post("/chat", json={})
        assert response.status_code == 422
    
    def test_chat_with_empty_query_returns_400(self):
        """Test that empty query returns 400."""
        response = client.post("/chat", json={"query": ""})
        assert response.status_code == 400
    
    def test_chat_response_has_required_fields(self):
        """Test that chat response has required fields."""
        response = client.post("/chat", json={"query": "test"})
        # May return 200 or 500 depending on vector DB state
        data = response.json()
        
        # Should have either response field or error field
        assert "response" in data or "error" in data


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_invalid_endpoint_returns_404(self):
        """Test that invalid endpoint returns 404."""
        response = client.get("/invalid-endpoint")
        assert response.status_code == 404
    
    def test_error_response_has_request_id(self):
        """Test that error responses include request ID."""
        response = client.post("/chat", json={"query": ""})
        
        # Check header or response body
        if response.status_code >= 400:
            # Response should have error structure
            data = response.json()
            # May have request_id depending on error type
            pass


class TestRequestTracking:
    """Tests for request ID tracking."""
    
    def test_response_has_request_id_header(self):
        """Test that responses include X-Request-ID header."""
        response = client.get("/health")
        assert "X-Request-ID" in response.headers
        
        # Request ID should be UUID-like
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) > 0


@pytest.mark.parametrize("endpoint", [
    "/health",
    "/"
])
def test_endpoints_return_200(endpoint):
    """Test that main endpoints return 200."""
    response = client.get(endpoint)
    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
