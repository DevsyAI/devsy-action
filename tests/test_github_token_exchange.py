"""Tests for github_token_exchange.py"""

import json
import os
import pytest
import responses
from unittest.mock import patch, MagicMock
from src.github_token_exchange import (
    get_github_token,
    exchange_for_devsy_bot_token,
    set_github_output,
    main
)


class TestSetGithubOutput:
    """Test GitHub output setting."""

    def test_set_github_output_with_file(self, tmp_path):
        """Test setting output when GITHUB_OUTPUT exists."""
        output_file = tmp_path / "output"
        output_file.write_text("")
        
        with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output_file)}):
            set_github_output("key", "value")
        
        content = output_file.read_text()
        assert "key=value" in content

    def test_set_github_output_no_file(self, capsys):
        """Test setting output when GITHUB_OUTPUT doesn't exist."""
        with patch.dict(os.environ, {}, clear=True):
            set_github_output("key", "value")
        
        captured = capsys.readouterr()
        assert "key=value" in captured.out


# Note: get_oidc_token is not a public function in the module, 
# so we'll test it indirectly through exchange_for_devsy_bot_token


class TestExchangeForDevsyBotToken:
    """Test devsy-bot token exchange."""

    @responses.activate
    def test_exchange_success(self):
        """Test successful token exchange."""
        responses.add(
            responses.POST,
            "https://devsy.ai/api/github-token-exchange",
            json={"github_token": "new-devsy-token"},
            status=200
        )
        
        # Mock environment for successful exchange
        with patch.dict(os.environ, {
            'GITHUB_REPOSITORY': 'owner/repo',
            'DEVSY_BACKEND_URL': 'https://devsy.ai',
            'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://github-oidc.com/token',
            'ACTIONS_ID_TOKEN_REQUEST_TOKEN': 'request-token'
        }):
            # Mock the OIDC token endpoint
            responses.add(
                responses.GET,
                "https://github-oidc.com/token",
                json={"value": "oidc-token"},
                status=200
            )
            result = exchange_for_devsy_bot_token("github-token")
        
        assert result == "new-devsy-token"

    def test_exchange_no_oidc_env(self):
        """Test token exchange when OIDC environment is not available."""
        with patch.dict(os.environ, {'GITHUB_REPOSITORY': 'owner/repo'}, clear=True):
            result = exchange_for_devsy_bot_token("github-token")
        
        assert result is None

    @responses.activate
    def test_exchange_api_failure(self):
        """Test token exchange when API call fails."""
        responses.add(
            responses.POST,
            "https://devsy.ai/api/github-token-exchange",
            status=400
        )
        
        with patch.dict(os.environ, {
            'GITHUB_REPOSITORY': 'owner/repo',
            'DEVSY_BACKEND_URL': 'https://devsy.ai',
            'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://github-oidc.com/token',
            'ACTIONS_ID_TOKEN_REQUEST_TOKEN': 'request-token'
        }):
            # Mock OIDC endpoint
            responses.add(
                responses.GET,
                "https://github-oidc.com/token",
                json={"value": "oidc-token"},
                status=200
            )
            result = exchange_for_devsy_bot_token("github-token")
        
        assert result is None

    def test_exchange_missing_repository(self):
        """Test token exchange with missing repository environment."""
        with patch.dict(os.environ, {}, clear=True):
            result = exchange_for_devsy_bot_token("github-token")
        
        assert result is None

    @responses.activate
    def test_exchange_request_data(self):
        """Test that exchange sends correct request data."""
        responses.add(
            responses.POST,
            "https://devsy.ai/api/github-token-exchange",
            json={"github_token": "new-token"},
            status=200
        )
        
        with patch.dict(os.environ, {
            'GITHUB_REPOSITORY': 'owner/repo',
            'DEVSY_BACKEND_URL': 'https://devsy.ai',
            'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://github-oidc.com/token',
            'ACTIONS_ID_TOKEN_REQUEST_TOKEN': 'request-token'
        }):
            # Mock OIDC endpoint
            responses.add(
                responses.GET,
                "https://github-oidc.com/token",
                json={"value": "test-oidc"},
                status=200
            )
            exchange_for_devsy_bot_token("test-github-token")
        
        # Verify the request was made correctly
        assert len(responses.calls) == 1
        request = responses.calls[0].request
        request_data = json.loads(request.body)
        
        assert request_data["github_token"] == "test-github-token"
        assert request_data["github_oidc_token"] == "test-oidc"
        assert request_data["repository"] == "owner/repo"


class TestGetGithubToken:
    """Test main token retrieval logic."""

    def test_get_github_token_override(self, tmp_path):
        """Test using override token."""
        output_file = tmp_path / "output"
        output_file.write_text("")
        
        with patch.dict(os.environ, {
            'OVERRIDE_GITHUB_TOKEN': 'override-token',
            'GITHUB_OUTPUT': str(output_file)
        }):
            result = get_github_token()
        
        assert result == "override-token"
        content = output_file.read_text()
        assert "github_token=override-token" in content

    def test_get_github_token_no_github_token(self):
        """Test when GITHUB_TOKEN is not set."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GITHUB_TOKEN environment variable is required"):
                get_github_token()

    @patch('src.github_token_exchange.exchange_for_devsy_bot_token')
    def test_get_github_token_successful_exchange(self, mock_exchange, tmp_path):
        """Test successful devsy-bot token exchange."""
        output_file = tmp_path / "output"
        output_file.write_text("")
        
        mock_exchange.return_value = "devsy-token"
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'github-token',
            'GITHUB_OUTPUT': str(output_file)
        }):
            result = get_github_token()
        
        assert result == "devsy-token"
        mock_exchange.assert_called_once_with("github-token")

    @patch('src.github_token_exchange.exchange_for_devsy_bot_token')
    def test_get_github_token_exchange_failure(self, mock_exchange, tmp_path, capsys):
        """Test fallback when exchange fails."""
        output_file = tmp_path / "output"
        output_file.write_text("")
        
        mock_exchange.return_value = None
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'github-token',
            'GITHUB_OUTPUT': str(output_file)
        }):
            result = get_github_token()
        
        assert result == "github-token"
        captured = capsys.readouterr()
        assert "Failed to exchange for devsy-bot token, using GitHub Actions token" in captured.out

    @patch('src.github_token_exchange.exchange_for_devsy_bot_token')
    def test_get_github_token_exchange_exception(self, mock_exchange, tmp_path, capsys):
        """Test fallback when exchange raises exception."""
        output_file = tmp_path / "output"
        output_file.write_text("")
        
        mock_exchange.side_effect = Exception("API error")
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'github-token',
            'GITHUB_OUTPUT': str(output_file)
        }):
            result = get_github_token()
        
        assert result == "github-token"
        captured = capsys.readouterr()
        assert "Error during token exchange" in captured.out


class TestMain:
    """Test main function."""

    @patch('src.github_token_exchange.get_github_token')
    def test_main_success(self, mock_get_token):
        """Test successful main execution."""
        mock_get_token.return_value = "test-token"
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    @patch('src.github_token_exchange.get_github_token')
    def test_main_exception(self, mock_get_token, capsys):
        """Test main with exception."""
        mock_get_token.side_effect = Exception("Token error")
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        
        captured = capsys.readouterr()
        assert "Error getting GitHub token" in captured.out