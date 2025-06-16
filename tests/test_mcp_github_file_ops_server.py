"""Tests for the GitHub file operations MCP server."""

import pytest
from unittest.mock import patch, Mock, MagicMock
import json
import base64

# Import the functions directly since the MCP decorators make testing harder
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'mcp'))
from github_file_ops_server import make_github_request, push_changes_impl, extract_local_commit_info, add_comment_impl


class TestMakeGithubRequest:
    """Test the make_github_request helper function."""
    
    @patch('github_file_ops_server.requests.request')
    def test_successful_request(self, mock_request):
        """Test successful GitHub API request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = '{"key": "value"}'
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response
        
        result = make_github_request(
            "GET",
            "https://api.github.com/repos/owner/repo/pulls/1",
            "token123"
        )
        
        assert result == {"key": "value"}
        mock_request.assert_called_once()
        
    @patch('github_file_ops_server.requests.request')
    def test_failed_request(self, mock_request):
        """Test failed GitHub API request."""
        # Mock failed response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_request.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            make_github_request(
                "GET",
                "https://api.github.com/repos/owner/repo/pulls/999",
                "token123"
            )
            
        assert "GitHub API error: 404" in str(exc_info.value)


class TestExtractLocalCommitInfo:
    """Test the extract_local_commit_info function."""
    
    @patch('github_file_ops_server.subprocess.run')
    def test_extract_commit_info_success(self, mock_run):
        """Test successful extraction of commit info."""
        # Mock git command outputs
        mock_run.side_effect = [
            Mock(stdout="Add new feature\n\nThis adds functionality X", returncode=0),  # git log message
            Mock(stdout="John Doe", returncode=0),  # git log author name
            Mock(stdout="john@example.com", returncode=0),  # git log author email
            Mock(stdout="src/file1.py\nsrc/file2.py\n", returncode=0),  # git diff-tree files
        ]
        
        result = extract_local_commit_info("HEAD")
        
        assert result["message"] == "Add new feature\n\nThis adds functionality X"
        assert result["author_name"] == "John Doe"
        assert result["author_email"] == "john@example.com"
        assert result["files"] == ["src/file1.py", "src/file2.py"]
        
        # Verify git commands were called correctly
        assert mock_run.call_count == 4
        mock_run.assert_any_call(
            ["git", "log", "-1", "--pretty=%B", "HEAD"],
            capture_output=True, text=True, check=True, cwd=os.getcwd()
        )
    
    @patch('github_file_ops_server.subprocess.run')
    def test_extract_commit_info_git_failure(self, mock_run):
        """Test handling of git command failure."""
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git', stderr="Git command failed")
        
        with pytest.raises(Exception) as exc_info:
            extract_local_commit_info("HEAD")
        
        assert "Failed to extract commit info" in str(exc_info.value)
    
    @patch('github_file_ops_server.subprocess.run')
    def test_extract_commit_info_no_files(self, mock_run):
        """Test extraction when no files changed."""
        mock_run.side_effect = [
            Mock(stdout="Empty commit", returncode=0),
            Mock(stdout="John Doe", returncode=0),
            Mock(stdout="john@example.com", returncode=0),
            Mock(stdout="", returncode=0),  # No files changed
        ]
        
        result = extract_local_commit_info("HEAD")
        
        assert result["message"] == "Empty commit"
        assert result["files"] == []


class TestPushChanges:
    """Test the new push_changes_impl function (recreate local commits)."""
    
    @patch('github_file_ops_server.extract_local_commit_info')
    @patch('github_file_ops_server.make_github_request')
    @patch('github_file_ops_server.os.path.exists')
    @patch('builtins.open')
    @patch('github_file_ops_server.subprocess.run')
    def test_push_changes_success(self, mock_subprocess, mock_open, mock_exists, mock_github_request, mock_extract):
        """Test successful recreation of local commit."""
        # Mock local commit extraction
        mock_extract.return_value = {
            "message": "Address review feedback: fix bug in validation",
            "author_name": "John Doe",
            "author_email": "john@example.com",
            "files": ["src/validator.py", "tests/test_validator.py"]
        }
        
        # Mock file system
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "# Fixed code here"
        
        # Mock git rev-parse to get original SHA
        mock_subprocess.return_value = Mock(stdout="abc123local", returncode=0)
        
        # Mock GitHub API responses
        mock_github_request.side_effect = [
            # Get branch reference
            {"object": {"sha": "base123"}},
            # Get base commit
            {"tree": {"sha": "tree123"}},
            # Create blob for first file
            {"sha": "blob1"},
            # Create blob for second file
            {"sha": "blob2"},
            # Create tree
            {"sha": "newtree123"},
            # Create commit
            {"sha": "newcommit123", "html_url": "https://github.com/owner/repo/commit/newcommit123"},
            # Update reference
            {"ref": "refs/heads/main"}
        ]
        
        result = push_changes_impl(
            commit_ref="HEAD",
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is True
        assert result["original_local_sha"] == "abc123local"
        assert result["github_sha"] == "newcommit123"
        assert result["url"] == "https://github.com/owner/repo/commit/newcommit123"
        assert "2 file(s)" in result["message"]
        assert result["files_changed"] == ["src/validator.py", "tests/test_validator.py"]
        
        # Verify commit was created with correct author info - it's the 4th argument (data parameter)
        commit_calls = [call for call in mock_github_request.call_args_list 
                       if len(call.args) >= 2 and call.args[0] == "POST" and "commits" in call.args[1]]
        
        assert len(commit_calls) == 1
        commit_call = commit_calls[0]
        
        # The data is passed as the 4th positional argument (index 3)
        commit_data = commit_call.args[3]
        assert commit_data["message"] == "Address review feedback: fix bug in validation"
        assert commit_data["author"]["name"] == "John Doe"
        assert commit_data["author"]["email"] == "john@example.com"
    
    @patch('github_file_ops_server.extract_local_commit_info')
    @patch('github_file_ops_server.make_github_request')
    @patch('github_file_ops_server.os.path.exists')
    @patch('builtins.open')
    def test_push_changes_with_deletions(self, mock_open, mock_exists, mock_github_request, mock_extract):
        """Test pushing changes that include file deletions."""
        # Mock local commit extraction
        mock_extract.return_value = {
            "message": "Remove deprecated files",
            "author_name": "Jane Smith",
            "author_email": "jane@example.com",
            "files": ["src/new.py", "old_file.py"]  # old_file.py was deleted
        }
        
        # Mock file system - new.py exists, old_file.py doesn't
        def exists_side_effect(path):
            return path == "src/new.py"
        
        mock_exists.side_effect = exists_side_effect
        mock_open.return_value.__enter__.return_value.read.return_value = "New code"
        
        # Mock GitHub API responses
        mock_github_request.side_effect = [
            {"object": {"sha": "base123"}},
            {"tree": {"sha": "tree123"}},
            {"sha": "blob1"},  # blob for new.py
            {"sha": "newtree123"},
            {"sha": "newcommit123", "html_url": "https://github.com/owner/repo/commit/newcommit123"},
            {"ref": "refs/heads/main"}
        ]
        
        result = push_changes_impl(
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is True
        assert result["github_sha"] == "newcommit123"
        
        # Verify tree creation includes both addition and deletion
        tree_calls = [call for call in mock_github_request.call_args_list 
                     if len(call.args) >= 2 and call.args[0] == "POST" and "trees" in call.args[1]]
        
        assert len(tree_calls) == 1
        tree_call = tree_calls[0]
        
        # The data is passed as the 4th positional argument (index 3)
        tree_data = tree_call.args[3]
        tree_entries = tree_data["tree"]
        assert len(tree_entries) == 2
        
        # Check that new.py was added with blob SHA
        new_file_entry = next(e for e in tree_entries if e["path"] == "src/new.py")
        assert new_file_entry["sha"] == "blob1"
        
        # Check that old_file.py was deleted (sha: null)
        deleted_file_entry = next(e for e in tree_entries if e["path"] == "old_file.py")
        assert deleted_file_entry["sha"] is None
    
    @patch('github_file_ops_server.extract_local_commit_info')
    def test_push_changes_no_files_changed(self, mock_extract):
        """Test error when no files changed in commit."""
        mock_extract.return_value = {
            "message": "Empty commit",
            "author_name": "John Doe",
            "author_email": "john@example.com",
            "files": []
        }
        
        result = push_changes_impl(
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "No files changed in the specified commit" in result["error"]
    
    @patch('github_file_ops_server.extract_local_commit_info')
    def test_push_changes_extract_failure(self, mock_extract):
        """Test handling of commit extraction failure."""
        mock_extract.side_effect = Exception("Git error: not a git repository")
        
        result = push_changes_impl(
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "Git error: not a git repository" in result["error"]
    
    @patch('github_file_ops_server.extract_local_commit_info')
    @patch('github_file_ops_server.make_github_request')
    def test_push_changes_api_failure(self, mock_github_request, mock_extract):
        """Test handling of GitHub API failure."""
        mock_extract.return_value = {
            "message": "Test commit",
            "author_name": "John Doe", 
            "author_email": "john@example.com",
            "files": ["test.py"]
        }
        
        mock_github_request.side_effect = Exception("GitHub API error")
        
        result = push_changes_impl(
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "GitHub API error" in result["error"]
    
    def test_push_changes_missing_parameters(self):
        """Test error handling for missing parameters."""
        result = push_changes_impl()  # No parameters provided
        
        assert result["success"] is False
        assert "Missing required parameters" in result["error"]


class TestAddComment:
    """Test the add_comment_impl function."""
    
    @patch('github_file_ops_server.make_github_request')
    def test_add_comment_success(self, mock_github_request):
        """Test successful PR comment addition."""
        # Mock the GitHub API response
        mock_github_request.return_value = {
            "id": 123456789,
            "html_url": "https://github.com/owner/repo/pull/550#issuecomment-123456789",
            "body": "## Test Comment\n\nThis is a test comment with `code` formatting."
        }
        
        result = add_comment_impl(
            pr_number=550,
            body="## Test Comment\n\nThis is a test comment with `code` formatting.",
            owner="testowner",
            repo="testrepo",
            github_token="token123"
        )
        
        assert result["success"] is True
        assert result["comment_id"] == 123456789
        assert result["url"] == "https://github.com/owner/repo/pull/550#issuecomment-123456789"
        assert result["body"] == "## Test Comment\n\nThis is a test comment with `code` formatting."
        assert "Successfully added comment to PR #550" in result["message"]
        
        # Verify the GitHub API was called correctly
        mock_github_request.assert_called_once_with(
            "POST",
            "https://api.github.com/repos/testowner/testrepo/issues/550/comments",
            "token123",
            {"body": "## Test Comment\n\nThis is a test comment with `code` formatting."}
        )
    
    @patch('github_file_ops_server.make_github_request')
    def test_add_comment_with_markdown(self, mock_github_request):
        """Test adding comment with complex markdown formatting."""
        markdown_body = """## ✅ Review Feedback Addressed

**Changes Made:**

### 1. Fixed Function Usage
- Issue: Replaced `warnings.warn()` with `print()` statement
- Location: `core/utils/logger.py:42`
- Rationale: Simpler approach without importing warnings module

### 2. Code Examples
```python
def example_function():
    return "Hello World"
```

**Key Points:**
- Repository context flows correctly
- Both workflows receive same `repository` object
- Testing confirmed for GitHub Actions workflow

All requested changes implemented."""
        
        mock_github_request.return_value = {
            "id": 987654321,
            "html_url": "https://github.com/owner/repo/pull/123#issuecomment-987654321",
            "body": markdown_body
        }
        
        result = add_comment_impl(
            pr_number=123,
            body=markdown_body,
            owner="testowner",
            repo="testrepo", 
            github_token="token123"
        )
        
        assert result["success"] is True
        assert result["comment_id"] == 987654321
        assert "Successfully added comment to PR #123" in result["message"]
        
        # Verify the complex markdown was passed through correctly
        call_args = mock_github_request.call_args
        assert call_args[0][3]["body"] == markdown_body
    
    def test_add_comment_missing_parameters(self):
        """Test error when required parameters are missing."""
        result = add_comment_impl(
            pr_number=123,
            body="Test comment"
            # Missing owner, repo, github_token
        )
        
        assert result["success"] is False
        assert "Missing required parameters: owner, repo, or github_token" in result["error"]
    
    def test_add_comment_empty_body(self):
        """Test error when comment body is empty."""
        result = add_comment_impl(
            pr_number=123,
            body="",
            owner="testowner",
            repo="testrepo",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "Comment body cannot be empty" in result["error"]
    
    def test_add_comment_whitespace_only_body(self):
        """Test error when comment body is only whitespace."""
        result = add_comment_impl(
            pr_number=123,
            body="   \n\t  ",
            owner="testowner",
            repo="testrepo",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "Comment body cannot be empty" in result["error"]
    
    @patch('github_file_ops_server.make_github_request')
    def test_add_comment_api_failure(self, mock_github_request):
        """Test handling of GitHub API failure."""
        mock_github_request.side_effect = Exception("GitHub API error: 404 Not found")
        
        result = add_comment_impl(
            pr_number=999,
            body="Test comment",
            owner="testowner",
            repo="testrepo",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "GitHub API error: 404 Not found" in result["error"]
    
    @patch('github_file_ops_server.make_github_request')
    def test_add_comment_with_env_vars(self, mock_github_request):
        """Test using environment variables for repo context."""
        with patch.dict('os.environ', {
            'REPO_OWNER': 'env-owner',
            'REPO_NAME': 'env-repo',
            'GITHUB_TOKEN': 'env-token'
        }):
            mock_github_request.return_value = {
                "id": 555,
                "html_url": "https://github.com/env-owner/env-repo/pull/42#issuecomment-555",
                "body": "Environment test"
            }
            
            result = add_comment_impl(
                pr_number=42,
                body="Environment test"
                # No explicit owner, repo, github_token - should use env vars
            )
            
            assert result["success"] is True
            assert result["comment_id"] == 555
            
            # Verify it used the environment variables
            mock_github_request.assert_called_once_with(
                "POST",
                "https://api.github.com/repos/env-owner/env-repo/issues/42/comments",
                "env-token",
                {"body": "Environment test"}
            )
    
    @patch('github_file_ops_server.make_github_request')
    def test_add_comment_explicit_params_override_env(self, mock_github_request):
        """Test that explicit parameters override environment variables."""
        with patch.dict('os.environ', {
            'REPO_OWNER': 'env-owner',
            'REPO_NAME': 'env-repo', 
            'GITHUB_TOKEN': 'env-token'
        }):
            mock_github_request.return_value = {
                "id": 777,
                "html_url": "https://github.com/explicit-owner/explicit-repo/pull/99#issuecomment-777",
                "body": "Override test"
            }
            
            result = add_comment_impl(
                pr_number=99,
                body="Override test",
                owner="explicit-owner",  # Should override env var
                repo="explicit-repo",    # Should override env var
                github_token="explicit-token"  # Should override env var
            )
            
            assert result["success"] is True
            assert result["comment_id"] == 777
            
            # Verify it used the explicit parameters, not env vars
            mock_github_request.assert_called_once_with(
                "POST",
                "https://api.github.com/repos/explicit-owner/explicit-repo/issues/99/comments",
                "explicit-token",
                {"body": "Override test"}
            )
