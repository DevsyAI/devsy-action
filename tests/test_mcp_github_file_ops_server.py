"""Tests for the GitHub file operations MCP server."""

import pytest
from unittest.mock import patch, Mock, MagicMock
import json
import base64

# Import the functions directly since the MCP decorators make testing harder
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'mcp'))
from github_file_ops_server import make_github_request, push_changes_impl, commit_files_impl, delete_files_impl


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


class TestPushChanges:
    """Test the push_changes_impl function."""
    
    @patch('github_file_ops_server.make_github_request')
    def test_commit_files_only(self, mock_github_request):
        """Test committing files only."""
        # Mock the API responses in order
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
            message="Test commit",
            files=[
                {"path": "test.txt", "content": "Hello World"},
                {"path": "README.md", "content": "# Test"}
            ],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is True
        assert result["sha"] == "newcommit123"
        assert result["url"] == "https://github.com/owner/repo/commit/newcommit123"
        assert "2 file(s) and deleted 0 file(s)" in result["message"]
    
    @patch('github_file_ops_server.make_github_request')
    def test_delete_files_only(self, mock_github_request):
        """Test deleting files only."""
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
        
        result = push_changes_impl(
            message="Delete files",
            delete_paths=["delete.txt", "also-delete.txt"],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is True
        assert result["sha"] == "newcommit123"
        assert "0 file(s) and deleted 2 file(s)" in result["message"]
    
    @patch('github_file_ops_server.make_github_request')
    def test_commit_and_delete_files(self, mock_github_request):
        """Test both committing and deleting files in one operation."""
        # Mock the API responses in order
        mock_github_request.side_effect = [
            # Get branch reference
            {"object": {"sha": "base123"}},
            # Get base commit
            {"tree": {"sha": "tree123"}},
            # Create blob for new file
            {"sha": "blob1"},
            # Create tree
            {"sha": "newtree123"},
            # Create commit
            {"sha": "newcommit123", "html_url": "https://github.com/owner/repo/commit/newcommit123"},
            # Update reference
            {"ref": "refs/heads/main"}
        ]
        
        result = push_changes_impl(
            message="Refactor: replace old.txt with new.txt",
            files=[{"path": "new.txt", "content": "New content"}],
            delete_paths=["old.txt"],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is True
        assert result["sha"] == "newcommit123"
        assert "1 file(s) and deleted 1 file(s)" in result["message"]
    
    @patch('github_file_ops_server.make_github_request')
    def test_no_files_or_deletes(self, mock_github_request):
        """Test error when no files to commit or delete."""
        result = push_changes_impl(
            message="Empty operation",
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "No files to commit or delete" in result["error"]
    
    @patch('github_file_ops_server.make_github_request')
    def test_push_failure(self, mock_github_request):
        """Test push failure handling."""
        mock_github_request.side_effect = Exception("API Error")
        
        result = push_changes_impl(
            message="Test commit",
            files=[{"path": "test.txt", "content": "Hello"}],
            owner="testowner",
            repo="testrepo", 
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "API Error" in result["error"]
    
    @patch('github_file_ops_server.make_github_request')
    def test_missing_parameters(self, mock_github_request):
        """Test error handling for missing parameters."""
        result = push_changes_impl(
            message="Test commit",
            files=[{"path": "test.txt", "content": "Hello"}],
            # Missing required parameters
        )
        
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