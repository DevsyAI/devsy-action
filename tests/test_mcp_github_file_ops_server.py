"""Tests for the GitHub file operations MCP server."""

import pytest
from unittest.mock import patch, Mock, MagicMock
import json
import base64

# Import the functions directly since the MCP decorators make testing harder
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'mcp'))
from github_file_ops_server import make_github_request, push_changes_impl, commit_files_impl, delete_files_impl, extract_local_commit_info


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


class TestCommitFiles:
    """Test the commit_files_impl function."""
    
    @patch('github_file_ops_server.make_github_request')
    @patch('github_file_ops_server.os.path.exists')
    @patch('builtins.open')
    def test_commit_files_success(self, mock_open, mock_exists, mock_github_request):
        """Test successful file commit."""
        # Mock file system
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "Hello World"
        
        # Mock the API responses in order
        mock_github_request.side_effect = [
            # Get branch reference
            {"object": {"sha": "base123"}},
            # Get base commit
            {"tree": {"sha": "tree123"}},
            # Create blob for file
            {"sha": "blob1"},
            # Create tree
            {"sha": "newtree123"},
            # Create commit
            {"sha": "newcommit123", "html_url": "https://github.com/owner/repo/commit/newcommit123"},
            # Update reference
            {"ref": "refs/heads/main"}
        ]
        
        result = commit_files_impl(
            message="Test commit",
            files=["test.txt"],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is True
        assert result["sha"] == "newcommit123"
        assert result["url"] == "https://github.com/owner/repo/commit/newcommit123"
        assert "1 file(s)" in result["message"]
        
        # Verify file was read
        mock_open.assert_called_with("test.txt", 'r', encoding='utf-8')
    
    @patch('github_file_ops_server.os.path.exists')
    def test_commit_files_file_not_found(self, mock_exists):
        """Test error when file doesn't exist."""
        mock_exists.return_value = False
        
        result = commit_files_impl(
            message="Test commit",
            files=["nonexistent.txt"],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "File not found: nonexistent.txt" in result["error"]
    
    @patch('github_file_ops_server.make_github_request')
    @patch('github_file_ops_server.os.path.exists')
    @patch('builtins.open')
    def test_commit_files_binary_file(self, mock_open, mock_exists, mock_github_request):
        """Test committing binary files."""
        # Mock file system
        mock_exists.return_value = True
        
        # Mock the text file read to raise UnicodeDecodeError, then binary read
        text_file_mock = MagicMock()
        text_file_mock.__enter__.return_value.read.side_effect = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')
        
        binary_file_mock = MagicMock()
        binary_file_mock.__enter__.return_value.read.return_value = b'\x89PNG\r\n\x1a\n'
        
        mock_open.side_effect = [text_file_mock, binary_file_mock]
        
        # Mock the API responses
        mock_github_request.side_effect = [
            {"object": {"sha": "base123"}},
            {"tree": {"sha": "tree123"}},
            {"sha": "blob1"},
            {"sha": "newtree123"},
            {"sha": "newcommit123", "html_url": "https://github.com/owner/repo/commit/newcommit123"},
            {"ref": "refs/heads/main"}
        ]
        
        result = commit_files_impl(
            message="Add binary file",
            files=["image.png"],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is True
        # Verify both text and binary open calls
        assert mock_open.call_count == 2
    
    def test_commit_files_no_files(self):
        """Test error when no files provided."""
        result = commit_files_impl(
            message="Empty commit",
            files=[],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "No files to commit" in result["error"]


class TestDeleteFiles:
    """Test the delete_files_impl function."""
    
    @patch('github_file_ops_server.make_github_request')
    def test_delete_files_success(self, mock_github_request):
        """Test successful file deletion."""
        # Mock the API responses in order
        mock_github_request.side_effect = [
            # Get branch reference
            {"object": {"sha": "base123"}},
            # Get base commit
            {"tree": {"sha": "tree123"}},
            # Create tree
            {"sha": "newtree123"},
            # Create commit
            {"sha": "newcommit123", "html_url": "https://github.com/owner/repo/commit/newcommit123"},
            # Update reference
            {"ref": "refs/heads/main"}
        ]
        
        result = delete_files_impl(
            message="Delete old files",
            files=["old.txt", "deprecated.js"],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is True
        assert result["sha"] == "newcommit123"
        assert result["url"] == "https://github.com/owner/repo/commit/newcommit123"
        assert "2 file(s)" in result["message"]
    
    def test_delete_files_no_files(self):
        """Test error when no files provided."""
        result = delete_files_impl(
            message="Empty deletion",
            files=[],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "No files to delete" in result["error"]
    
    @patch('github_file_ops_server.make_github_request')
    def test_delete_files_api_failure(self, mock_github_request):
        """Test deletion failure handling."""
        mock_github_request.side_effect = Exception("API Error")
        
        result = delete_files_impl(
            message="Delete files",
            files=["file.txt"],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "API Error" in result["error"]
    
    def test_delete_files_missing_parameters(self):
        """Test error handling for missing parameters."""
        result = delete_files_impl(
            message="Delete files",
            files=["file.txt"],
            # Missing required parameters
        )
        
        assert result["success"] is False
        assert "Missing required parameters" in result["error"]