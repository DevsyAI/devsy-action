"""Tests for send_callback.py"""

import pytest
import responses
from unittest.mock import patch
from datetime import datetime, timezone
from src.send_callback import (
    prepare_callback_data,
    prepare_headers,
    send_callback,
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

    def test_timestamp_format(self):
        """Test that timestamp is in correct ISO format."""
        result = prepare_callback_data(
            "123", "url", "mode", "success", "", "", "", "file", "source"
        )
        
        timestamp = result["timestamp"]
        # Should be able to parse the timestamp
        parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert parsed.tzinfo == timezone.utc


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


class TestMain:
    """Test main function."""

    @responses.activate
    @patch('sys.argv', [
        'send_callback.py',
        '--callback-url', 'https://example.com/callback',
        '--run-id', '123',
        '--run-url', 'https://github.com/owner/repo/actions/runs/123',
        '--mode', 'pr-gen',
        '--conclusion', 'success',
        '--execution-file', 'exec.json',
        '--token-source', 'devsy-bot',
        '--repository', 'owner/repo'
    ])
    def test_main_success(self, capsys):
        """Test successful main execution."""
        responses.add(
            responses.POST,
            "https://example.com/callback",
            status=200
        )
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        
        captured = capsys.readouterr()
        assert "📤 Sending callback to" in captured.out
        assert "✅ Callback sent successfully" in captured.out

    @responses.activate
    @patch('sys.argv', [
        'send_callback.py',
        '--callback-url', 'https://example.com/callback',
        '--run-id', '123',
        '--run-url', 'https://github.com/owner/repo/actions/runs/123',
        '--mode', 'pr-update',
        '--conclusion', 'failure',
        '--pr-number', '456',
        '--pr-url', 'https://github.com/owner/repo/pull/456',
        '--execution-file', 'exec.json',
        '--token-source', 'github-actions-bot',
        '--auth-token', 'secret123',
        '--repository', 'owner/repo'
    ])
    def test_main_with_auth(self, capsys):
        """Test main with authentication."""
        responses.add(
            responses.POST,
            "https://example.com/callback",
            status=200
        )
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        
        captured = capsys.readouterr()
        assert "📤 Sending authenticated callback" in captured.out

    @responses.activate
    @patch('sys.argv', [
        'send_callback.py',
        '--callback-url', 'https://example.com/callback',
        '--run-id', '123',
        '--run-url', 'https://github.com/owner/repo/actions/runs/123',
        '--mode', 'plan-gen',
        '--conclusion', 'success',
        '--plan-output', 'Detailed implementation plan',
        '--execution-file', 'exec.json',
        '--token-source', 'devsy-bot',
        '--repository', 'owner/repo'
    ])
    def test_main_plan_gen_mode(self):
        """Test main with plan generation mode."""
        responses.add(
            responses.POST,
            "https://example.com/callback",
            status=200
        )
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    @responses.activate
    @patch('sys.argv', [
        'send_callback.py',
        '--callback-url', 'https://example.com/callback',
        '--run-id', '123',
        '--run-url', 'https://github.com/owner/repo/actions/runs/123',
        '--mode', 'pr-gen',
        '--conclusion', 'success',
        '--execution-file', 'exec.json',
        '--token-source', 'devsy-bot',
        '--repository', 'owner/repo'
    ])
    def test_main_callback_failure_still_exits_zero(self, capsys):
        """Test that callback failure doesn't fail the action."""
        responses.add(
            responses.POST,
            "https://example.com/callback",
            status=500
        )
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        # Should still exit with 0 to not fail the action
        assert exc_info.value.code == 0
        
        captured = capsys.readouterr()
        assert "⚠️  Warning: Failed to send callback" in captured.out