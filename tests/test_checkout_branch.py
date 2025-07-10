"""Tests for checkout_branch.py"""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest
import responses
from src.checkout_branch import checkout_pr_branch, fetch_github_data, main, run_git_command


class TestFetchGithubData:
    """Test GitHub API data fetching."""

    @responses.activate
    def test_fetch_github_data_success(self):
        """Test successful GitHub API call."""
        endpoint = "https://api.github.com/repos/owner/repo/pulls/123"
        token = "test-token"
        mock_response = {"number": 123, "title": "Test PR"}

        responses.add(
            responses.GET,
            endpoint,
            json=mock_response,
            status=200
        )

        result = fetch_github_data(endpoint, token)
        assert result == mock_response

        # Verify headers
        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert request.headers["Authorization"] == "token test-token"
        assert request.headers["Accept"] == "application/vnd.github.v3+json"

    @responses.activate
    def test_fetch_github_data_failure(self):
        """Test GitHub API failure."""
        endpoint = "https://api.github.com/repos/owner/repo/pulls/123"
        token = "test-token"

        responses.add(
            responses.GET,
            endpoint,
            status=404
        )

        with pytest.raises(Exception):
            fetch_github_data(endpoint, token)


class TestRunGitCommand:
    """Test git command execution."""

    @patch('subprocess.run')
    def test_run_git_command_success(self, mock_run):
        """Test successful git command execution."""
        mock_run.return_value = MagicMock(
            stdout="main\n",
            stderr="",
            returncode=0
        )

        result = run_git_command(["git", "branch", "--show-current"], "getting current branch")
        assert result == "main"

        mock_run.assert_called_once_with(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
            cwd=os.getcwd()
        )

    @patch('subprocess.run')
    def test_run_git_command_failure(self, mock_run):
        """Test git command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "branch"],
            stderr="fatal: not a git repository"
        )

        with pytest.raises(subprocess.CalledProcessError):
            run_git_command(["git", "branch"], "listing branches")


class TestCheckoutPrBranch:
    """Test PR branch checkout functionality."""

    @responses.activate
    @patch('src.checkout_branch.run_git_command')
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

        # Verify git commands were called in order
        assert mock_git.call_count == 3
        calls = mock_git.call_args_list
        assert calls[0][0] == (["git", "fetch", "origin", "feature-branch"], "fetching branch")
        assert calls[1][0] == (["git", "checkout", "feature-branch"], "checking out branch")
        assert calls[2][0] == (["git", "branch", "--show-current"], "getting current branch")

    @responses.activate
    @patch('src.checkout_branch.run_git_command')
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
        assert result["head_branch"] == "feature-branch"
        assert result["base_branch"] == "main"
        assert result["current_branch"] == "feature-branch"
        assert result["is_fork_pr"] is True
        assert result["head_repo"] == "contributor/repo"

    @responses.activate
    @patch('src.checkout_branch.run_git_command')
    def test_checkout_pr_branch_api_failure(self, mock_git):
        """Test checkout failure due to GitHub API error."""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/pulls/123",
            status=404
        )

        result = checkout_pr_branch(123, "test-token", "owner/repo")

        assert result["success"] is False
        assert "error" in result
        mock_git.assert_not_called()

    @responses.activate
    @patch('src.checkout_branch.run_git_command')
    def test_checkout_pr_branch_git_failure(self, mock_git):
        """Test checkout failure due to git command error."""
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

        # Mock git fetch to fail
        mock_git.side_effect = subprocess.CalledProcessError(
            1, ["git", "fetch"], stderr="fatal: repository not found"
        )

        result = checkout_pr_branch(123, "test-token", "owner/repo")

        assert result["success"] is False
        assert "error" in result

    @responses.activate
    @patch('src.checkout_branch.run_git_command')
    def test_checkout_pr_branch_wrong_branch(self, mock_git):
        """Test checkout failure when ending up on wrong branch."""
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

        # Mock git commands to return wrong branch name
        def git_side_effect(command, description):
            if command == ["git", "branch", "--show-current"]:
                return "main"  # Wrong branch
            return ""

        mock_git.side_effect = git_side_effect

        result = checkout_pr_branch(123, "test-token", "owner/repo")

        assert result["success"] is False
        assert "Failed to checkout correct branch" in result["error"]


class TestMain:
    """Test main function."""

    @patch('src.checkout_branch.checkout_pr_branch')
    def test_main_pr_update_success(self, mock_checkout):
        """Test main function for pr-update mode success."""
        mock_checkout.return_value = {
            "success": True,
            "current_branch": "feature-branch"
        }

        env_vars = {
            "DEVSY_MODE": "pr-update",
            "DEVSY_PR_NUMBER": "123",
            "GITHUB_TOKEN": "test-token",
            "DEVSY_REPO": "owner/repo"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            main()  # Should not raise exception

        mock_checkout.assert_called_once_with(123, "test-token", "owner/repo")

    @patch('src.checkout_branch.checkout_pr_branch')
    def test_main_pr_update_failure(self, mock_checkout):
        """Test main function for pr-update mode failure."""
        mock_checkout.return_value = {
            "success": False,
            "error": "Checkout failed"
        }

        env_vars = {
            "DEVSY_MODE": "pr-update",
            "DEVSY_PR_NUMBER": "123",
            "GITHUB_TOKEN": "test-token",
            "DEVSY_REPO": "owner/repo"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

        mock_checkout.assert_called_once_with(123, "test-token", "owner/repo")

    def test_main_pr_gen_mode(self):
        """Test main function for pr-gen mode (no checkout needed)."""
        env_vars = {
            "DEVSY_MODE": "pr-gen",
            "GITHUB_TOKEN": "test-token",
            "DEVSY_REPO": "owner/repo"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            main()  # Should not raise exception

    def test_main_missing_mode(self):
        """Test main function with missing mode."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_missing_token(self):
        """Test main function with missing GitHub token."""
        env_vars = {
            "DEVSY_MODE": "pr-update",
            "DEVSY_REPO": "owner/repo"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_missing_repo(self):
        """Test main function with missing repository."""
        env_vars = {
            "DEVSY_MODE": "pr-update",
            "GITHUB_TOKEN": "test-token"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_missing_pr_number(self):
        """Test main function with missing PR number for pr-update mode."""
        env_vars = {
            "DEVSY_MODE": "pr-update",
            "GITHUB_TOKEN": "test-token",
            "DEVSY_REPO": "owner/repo"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_invalid_pr_number(self):
        """Test main function with invalid PR number."""
        env_vars = {
            "DEVSY_MODE": "pr-update",
            "DEVSY_PR_NUMBER": "not-a-number",
            "GITHUB_TOKEN": "test-token",
            "DEVSY_REPO": "owner/repo"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
