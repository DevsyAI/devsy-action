"""Tests for prepare_git.py"""

import json
import os
import pytest
import responses
import subprocess
from unittest.mock import patch, MagicMock, call
from src.prepare_git import (
    set_github_output,
    get_oidc_token,
    exchange_for_devsy_bot_token,
    perform_token_exchange,
    run_command,
    configure_git_identity,
    fetch_github_data,
    run_git_command,
    checkout_pr_branch,
    handle_branch_checkout,
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
            # Check environment variable is set within the context
            assert os.environ.get("key") == "value"
        
        content = output_file.read_text()
        assert "key=value" in content

    def test_set_github_output_no_file(self):
        """Test setting output when GITHUB_OUTPUT doesn't exist."""
        with patch.dict(os.environ, {}, clear=True):
            set_github_output("key", "value")
            assert os.environ.get("key") == "value"


class TestGetOidcToken:
    """Test OIDC token retrieval."""

    @responses.activate
    def test_get_oidc_token_success(self):
        """Test successful OIDC token retrieval."""
        token_request_url = "https://api.github.com/token"
        token_request_token = "request-token"
        
        responses.add(
            responses.GET,
            f"{token_request_url}&audience=devsy-action",
            json={"value": "oidc-token"},
            status=200
        )
        
        with patch.dict(os.environ, {
            'ACTIONS_ID_TOKEN_REQUEST_URL': token_request_url,
            'ACTIONS_ID_TOKEN_REQUEST_TOKEN': token_request_token
        }):
            result = get_oidc_token()
        
        assert result == "oidc-token"

    def test_get_oidc_token_missing_env_vars(self):
        """Test OIDC token retrieval with missing environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OIDC token request environment variables not found"):
                get_oidc_token()

    @responses.activate
    def test_get_oidc_token_api_failure(self):
        """Test OIDC token retrieval with API failure."""
        token_request_url = "https://api.github.com/token"
        token_request_token = "request-token"
        
        responses.add(
            responses.GET,
            f"{token_request_url}&audience=devsy-action",
            status=401
        )
        
        with patch.dict(os.environ, {
            'ACTIONS_ID_TOKEN_REQUEST_URL': token_request_url,
            'ACTIONS_ID_TOKEN_REQUEST_TOKEN': token_request_token
        }):
            with pytest.raises(Exception, match="OIDC token request failed"):
                get_oidc_token()


class TestExchangeForDevsyBotToken:
    """Test devsy-bot token exchange."""

    @responses.activate
    def test_exchange_for_devsy_bot_token_success(self):
        """Test successful token exchange."""
        backend_url = "https://devsy.ai"
        oidc_token = "oidc-token"
        
        responses.add(
            responses.POST,
            f"{backend_url}/api/github-app/oidc-token-exchange",
            json={"access_token": "devsy-token"},
            status=200
        )
        
        with patch.dict(os.environ, {'DEVSY_BACKEND_URL': backend_url}):
            result = exchange_for_devsy_bot_token(oidc_token)
        
        assert result == "devsy-token"

    @responses.activate
    def test_exchange_for_devsy_bot_token_failure(self):
        """Test token exchange failure."""
        backend_url = "https://devsy.ai"
        oidc_token = "oidc-token"
        
        responses.add(
            responses.POST,
            f"{backend_url}/api/github-app/oidc-token-exchange",
            status=400
        )
        
        with patch.dict(os.environ, {'DEVSY_BACKEND_URL': backend_url}):
            with pytest.raises(Exception, match="Token exchange failed"):
                exchange_for_devsy_bot_token(oidc_token)


class TestPerformTokenExchange:
    """Test complete token exchange workflow."""

    def test_perform_token_exchange_override(self):
        """Test using override token."""
        with patch.dict(os.environ, {'OVERRIDE_GITHUB_TOKEN': 'override-token'}):
            token, source = perform_token_exchange()
        
        assert token == "override-token"
        assert source == "github-actions-bot"

    @patch('src.prepare_git.get_oidc_token')
    @patch('src.prepare_git.exchange_for_devsy_bot_token')
    def test_perform_token_exchange_successful_devsy(self, mock_exchange, mock_oidc):
        """Test successful devsy-bot token exchange."""
        mock_oidc.return_value = "oidc-token"
        mock_exchange.return_value = "devsy-token"
        
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'github-token'}):
            token, source = perform_token_exchange()
        
        assert token == "devsy-token"
        assert source == "devsy-bot"

    @patch('src.prepare_git.get_oidc_token')
    @patch('src.prepare_git.exchange_for_devsy_bot_token')
    def test_perform_token_exchange_fallback(self, mock_exchange, mock_oidc):
        """Test fallback to GitHub Actions token."""
        mock_oidc.side_effect = Exception("OIDC failed")
        
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'github-token'}):
            token, source = perform_token_exchange()
        
        assert token == "github-token"
        assert source == "github-actions-bot"

    def test_perform_token_exchange_no_fallback_token(self):
        """Test when no fallback token is available."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.prepare_git.get_oidc_token', side_effect=Exception("OIDC failed")):
                with pytest.raises(ValueError, match="GITHUB_TOKEN environment variable is required"):
                    perform_token_exchange()


class TestRunCommand:
    """Test command execution."""

    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test successful command execution."""
        mock_run.return_value = MagicMock(
            stdout="output",
            stderr="",
            returncode=0
        )
        
        result = run_command(["echo", "test"], "testing echo")
        assert result.stdout == "output"
        
        mock_run.assert_called_once_with(
            ["echo", "test"],
            capture_output=True,
            text=True,
            check=True,
            cwd=os.getcwd()
        )

    @patch('subprocess.run')
    def test_run_command_failure(self, mock_run):
        """Test command execution failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["false"],
            stderr="command failed"
        )
        
        with pytest.raises(subprocess.CalledProcessError):
            run_command(["false"], "testing failure")


class TestConfigureGitIdentity:
    """Test Git identity configuration."""

    @patch('src.prepare_git.run_command')
    def test_configure_git_identity_devsy_bot_success(self, mock_run):
        """Test Git configuration for devsy-bot token."""
        # Mock gh api user command to return bot info
        mock_run.side_effect = [
            MagicMock(stdout='{"login": "devsy-bot", "id": 12345}'),  # gh api user
            MagicMock(),  # git config email
            MagicMock(),  # git config name
            MagicMock(),  # git config https
        ]
        
        configure_git_identity("devsy-token", "devsy-bot")
        
        expected_calls = [
            call(["gh", "api", "user", "--jq", "{login: .login, id: .id}"], "getting bot identity"),
            call(["git", "config", "--global", "user.email", "12345+devsy-bot@users.noreply.github.com"], "setting git email"),
            call(["git", "config", "--global", "user.name", "devsy-bot"], "setting git name"),
            call(["git", "config", "--global", "url.https://github.com/.insteadOf", "git@github.com:"], "configuring git HTTPS"),
        ]
        
        mock_run.assert_has_calls(expected_calls)

    @patch('src.prepare_git.run_command')
    def test_configure_git_identity_devsy_bot_fallback(self, mock_run):
        """Test Git configuration for devsy-bot token with API failure."""
        # Mock gh api user command to fail, then fallback commands
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["gh"], stderr="API failed"),  # gh api user fails
            MagicMock(),  # git config email (fallback)
            MagicMock(),  # git config name (fallback)
            MagicMock(),  # git config https
        ]
        
        configure_git_identity("devsy-token", "devsy-bot")
        
        # Should attempt gh api first, then use fallback
        assert mock_run.call_count == 4
        mock_run.assert_any_call(["git", "config", "--global", "user.email", "no-reply@devsy.ai"], "setting fallback git email")

    @patch('src.prepare_git.run_command')
    def test_configure_git_identity_github_actions_bot(self, mock_run):
        """Test Git configuration for GitHub Actions token."""
        configure_git_identity("github-token", "github-actions-bot")
        
        expected_calls = [
            call(["git", "config", "--global", "user.email", "no-reply@devsy.ai"], "setting git email"),
            call(["git", "config", "--global", "user.name", "devsy-bot"], "setting git name"),
            call(["git", "config", "--global", "url.https://github.com/.insteadOf", "git@github.com:"], "configuring git HTTPS"),
        ]
        
        mock_run.assert_has_calls(expected_calls)


class TestCheckoutPrBranch:
    """Test PR branch checkout functionality."""

    @responses.activate
    @patch('src.prepare_git.run_git_command')
    def test_checkout_pr_branch_same_repo_success(self, mock_git):
        """Test successful checkout for same-repo PR."""
        # Mock GitHub API response
        pr_data = {
            "head": {
                "ref": "feature-branch",
                "repo": {"full_name": "owner/repo"}
            },
            "base": {
                "ref": "main"
            }
        }
        
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/pulls/123",
            json=pr_data,
            status=200
        )
        
        # Mock git commands - setup side effects for different commands
        def git_side_effect(command, description):
            if command == ["git", "branch", "--show-current"]:
                return "feature-branch"
            return ""
        
        mock_git.side_effect = git_side_effect
        
        result = checkout_pr_branch(123, "test-token", "owner/repo")
        
        assert result["success"] is True
        assert result["head_branch"] == "feature-branch"
        assert result["base_branch"] == "main"
        assert result["current_branch"] == "feature-branch"
        assert result["is_fork_pr"] is False
        assert result["head_repo"] == "owner/repo"

    @responses.activate
    @patch('src.prepare_git.run_git_command')
    def test_checkout_pr_branch_fork_success(self, mock_git):
        """Test successful checkout for fork PR."""
        # Mock GitHub API response for fork PR
        pr_data = {
            "head": {
                "ref": "feature-branch",
                "repo": {"full_name": "contributor/repo"}
            },
            "base": {
                "ref": "main"
            }
        }
        
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/pulls/123",
            json=pr_data,
            status=200
        )
        
        # Mock git commands - simulate remote add failing (already exists)
        def git_side_effect(command, description):
            if command == ["git", "remote", "add", "pr-fork", "https://github.com/contributor/repo.git"]:
                raise subprocess.CalledProcessError(1, command, stderr="remote already exists")
            elif command == ["git", "branch", "--show-current"]:
                return "feature-branch"
            return ""
        
        mock_git.side_effect = git_side_effect
        
        result = checkout_pr_branch(123, "test-token", "owner/repo")
        
        assert result["success"] is True
        assert result["is_fork_pr"] is True

    @responses.activate
    def test_checkout_pr_branch_api_failure(self):
        """Test checkout failure due to GitHub API error."""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/pulls/123",
            status=404
        )
        
        result = checkout_pr_branch(123, "test-token", "owner/repo")
        
        assert result["success"] is False
        assert "error" in result


class TestHandleBranchCheckout:
    """Test branch checkout handling."""

    @patch('src.prepare_git.checkout_pr_branch')
    def test_handle_branch_checkout_pr_update_success(self, mock_checkout):
        """Test successful branch checkout for pr-update mode."""
        mock_checkout.return_value = {
            "success": True,
            "current_branch": "feature-branch"
        }
        
        handle_branch_checkout("pr-update", "123", "test-token", "owner/repo")
        
        mock_checkout.assert_called_once_with(123, "test-token", "owner/repo")

    @patch('src.prepare_git.checkout_pr_branch')
    def test_handle_branch_checkout_pr_update_failure(self, mock_checkout):
        """Test branch checkout failure for pr-update mode."""
        mock_checkout.return_value = {
            "success": False,
            "error": "Checkout failed"
        }
        
        with pytest.raises(Exception, match="Checkout failed"):
            handle_branch_checkout("pr-update", "123", "test-token", "owner/repo")

    def test_handle_branch_checkout_pr_gen_mode(self):
        """Test branch checkout for pr-gen mode (no checkout needed)."""
        # Should not raise exception
        handle_branch_checkout("pr-gen", "", "test-token", "owner/repo")

    def test_handle_branch_checkout_missing_pr_number(self):
        """Test branch checkout with missing PR number for pr-update mode."""
        with pytest.raises(ValueError, match="DEVSY_PR_NUMBER environment variable is required"):
            handle_branch_checkout("pr-update", "", "test-token", "owner/repo")

    def test_handle_branch_checkout_invalid_pr_number(self):
        """Test branch checkout with invalid PR number."""
        with pytest.raises(ValueError, match="Invalid PR number"):
            handle_branch_checkout("pr-update", "not-a-number", "test-token", "owner/repo")


class TestMain:
    """Test main function."""

    @patch('src.prepare_git.perform_token_exchange')
    @patch('src.prepare_git.configure_git_identity')
    @patch('src.prepare_git.handle_branch_checkout')
    @patch('src.prepare_git.set_github_output')
    def test_main_success(self, mock_output, mock_checkout, mock_config, mock_exchange):
        """Test successful main function execution."""
        mock_exchange.return_value = ("test-token", "devsy-bot")
        
        env_vars = {
            "DEVSY_MODE": "pr-gen",
            "DEVSY_REPO": "owner/repo"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            main()
        
        mock_exchange.assert_called_once()
        mock_output.assert_any_call("github_token", "test-token")
        mock_output.assert_any_call("token_source", "devsy-bot")
        mock_config.assert_called_once_with("test-token", "devsy-bot")
        mock_checkout.assert_called_once_with("pr-gen", "", "test-token", "owner/repo")

    def test_main_missing_mode(self):
        """Test main function with missing mode."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_missing_repo(self):
        """Test main function with missing repository."""
        env_vars = {
            "DEVSY_MODE": "pr-gen"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch('src.prepare_git.perform_token_exchange')
    def test_main_token_exchange_failure(self, mock_exchange):
        """Test main function with token exchange failure."""
        mock_exchange.side_effect = Exception("Token exchange failed")
        
        env_vars = {
            "DEVSY_MODE": "pr-gen",
            "DEVSY_REPO": "owner/repo"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1