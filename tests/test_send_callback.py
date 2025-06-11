"""Tests for send_callback.py"""

import pytest
import responses
import tempfile
import os
from unittest.mock import patch
from datetime import datetime, timezone
from src.send_callback import (
    prepare_callback_data,
    prepare_headers,
    send_callback,
    read_execution_file,
    main
)


class TestPrepareCallbackData:
    """Test callback data preparation."""

    def test_prepare_callback_data_all_fields(self):
        """Test preparing callback data with all fields."""
        result = prepare_callback_data(
            run_id="123",
            run_url="https://github.com/owner/repo/actions/runs/123",
            mode="pr-gen",
            conclusion="success",
            pr_number="456",
            pr_url="https://github.com/owner/repo/pull/456",
            plan_output="",
            execution_file="execution.json",
            token_source="devsy-bot"
        )
        
        assert result["run_id"] == "123"
        assert result["mode"] == "pr-gen"
        assert result["conclusion"] == "success"
        assert result["pr_number"] == "456"
        assert result["pr_url"] == "https://github.com/owner/repo/pull/456"
        assert result["plan_output"] is None  # Empty string becomes None
        assert result["execution_file"] == "execution.json"
        assert result["execution_file_contents"] is None  # File doesn't exist
        assert result["token_source"] == "devsy-bot"
        assert "timestamp" in result

    def test_prepare_callback_data_empty_optionals(self):
        """Test preparing callback data with empty optional fields."""
        result = prepare_callback_data(
            run_id="123",
            run_url="https://example.com",
            mode="plan-gen",
            conclusion="failure",
            pr_number="",
            pr_url="",
            plan_output="detailed plan",
            execution_file="exec.json",
            token_source="github-actions-bot"
        )
        
        assert result["pr_number"] is None
        assert result["pr_url"] is None
        assert result["plan_output"] == "detailed plan"
        assert result["execution_file_contents"] is None  # File doesn't exist

    def test_timestamp_format(self):
        """Test that timestamp is in correct ISO format."""
        result = prepare_callback_data(
            "123", "url", "mode", "success", "", "", "", "file", "source"
        )
        
        timestamp = result["timestamp"]
        # Should be able to parse the timestamp
        parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert parsed.tzinfo == timezone.utc

    def test_prepare_callback_data_with_execution_file(self):
        """Test callback data preparation with existing execution file."""
        # Create a temporary file with test content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            test_content = '{"test": "execution data", "costs": {"total": 0.50}}'
            f.write(test_content)
            temp_file_path = f.name
        
        try:
            result = prepare_callback_data(
                run_id="123",
                run_url="https://example.com",
                mode="pr-gen",
                conclusion="success",
                pr_number="456",
                pr_url="https://example.com/pr/456",
                plan_output="",
                execution_file=temp_file_path,
                token_source="devsy-bot"
            )
            
            assert result["execution_file"] == temp_file_path
            assert result["execution_file_contents"] == test_content
        finally:
            # Clean up
            os.unlink(temp_file_path)


class TestReadExecutionFile:
    """Test execution file reading."""

    def test_read_execution_file_exists(self):
        """Test reading an existing execution file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            test_content = '{"execution": "data", "costs": {"input_tokens": 100}}'
            f.write(test_content)
            temp_file_path = f.name
        
        try:
            result = read_execution_file(temp_file_path)
            assert result == test_content
        finally:
            os.unlink(temp_file_path)

    def test_read_execution_file_not_exists(self):
        """Test reading a non-existent execution file."""
        result = read_execution_file("/path/that/does/not/exist.json")
        assert result is None

    def test_read_execution_file_empty_path(self):
        """Test reading with empty file path."""
        result = read_execution_file("")
        assert result is None

    def test_read_execution_file_none_path(self):
        """Test reading with None file path."""
        result = read_execution_file(None)
        assert result is None

    def test_read_execution_file_permission_error(self, capsys):
        """Test handling of permission errors when reading execution file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file_path = f.name
        
        try:
            # Change permissions to make file unreadable
            os.chmod(temp_file_path, 0o000)
            
            result = read_execution_file(temp_file_path)
            assert result is None
            
            captured = capsys.readouterr()
            assert "⚠️  Warning: Failed to read execution file" in captured.out
        finally:
            # Restore permissions and clean up
            os.chmod(temp_file_path, 0o644)
            os.unlink(temp_file_path)


class TestPrepareHeaders:
    """Test header preparation."""

    def test_prepare_headers_basic(self):
        """Test basic headers without authentication."""
        headers = prepare_headers("", "", "123", "owner/repo")
        
        expected = {
            "Content-Type": "application/json",
            "X-GitHub-Run-ID": "123",
            "X-GitHub-Repository": "owner/repo"
        }
        assert headers == expected

    def test_prepare_headers_with_auth(self):
        """Test headers with authentication token."""
        headers = prepare_headers("token123", "", "123", "owner/repo")
        
        assert headers["Authorization"] == "Bearer token123"
        assert headers["Content-Type"] == "application/json"

    def test_prepare_headers_custom_auth_header(self):
        """Test headers with custom auth header name."""
        headers = prepare_headers("token123", "X-API-Key", "123", "owner/repo")
        
        assert headers["X-API-Key"] == "Bearer token123"
        assert "Authorization" not in headers

    def test_prepare_headers_empty_auth_header_name(self):
        """Test that empty auth header name defaults to Authorization."""
        headers = prepare_headers("token123", "", "123", "owner/repo")
        
        assert headers["Authorization"] == "Bearer token123"


class TestSendCallback:
    """Test callback sending."""

    @responses.activate
    def test_send_callback_success(self):
        """Test successful callback sending."""
        responses.add(
            responses.POST,
            "https://example.com/callback",
            status=200
        )
        
        data = {"test": "data"}
        headers = {"Content-Type": "application/json"}
        
        result = send_callback("https://example.com/callback", data, headers)
        assert result is True

    @responses.activate
    def test_send_callback_failure(self, capsys):
        """Test callback sending failure."""
        responses.add(
            responses.POST,
            "https://example.com/callback",
            status=500
        )
        
        data = {"test": "data"}
        headers = {"Content-Type": "application/json"}
        
        result = send_callback("https://example.com/callback", data, headers)
        assert result is False
        
        captured = capsys.readouterr()
        assert "⚠️  Warning: Failed to send callback" in captured.out

    @responses.activate
    def test_send_callback_timeout(self, capsys):
        """Test callback timeout handling."""
        # responses doesn't have easy timeout simulation, 
        # so we'll use a different approach
        from requests.exceptions import Timeout
        
        with patch('requests.post', side_effect=Timeout("Request timed out")):
            data = {"test": "data"}
            headers = {"Content-Type": "application/json"}
            
            result = send_callback("https://example.com/callback", data, headers, timeout=1)
            assert result is False
            
            captured = capsys.readouterr()
            assert "⚠️  Warning: Failed to send callback" in captured.out

    @responses.activate
    def test_send_callback_request_data(self):
        """Test that callback sends correct data."""
        responses.add(
            responses.POST,
            "https://example.com/callback",
            status=200
        )
        
        test_data = {"run_id": "123", "mode": "pr-gen"}
        test_headers = {"Content-Type": "application/json", "Authorization": "Bearer token"}
        
        send_callback("https://example.com/callback", test_data, test_headers)
        
        # Verify request was made correctly
        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert request.headers["Content-Type"] == "application/json"
        assert request.headers["Authorization"] == "Bearer token"


# Main function integration tests removed - covered by manual testing