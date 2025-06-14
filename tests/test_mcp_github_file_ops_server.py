"""Tests for the GitHub file operations MCP server."""

import pytest
from unittest.mock import patch, Mock
import json
import base64

# Import the functions directly since the MCP decorators make testing harder
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'mcp'))
from github_file_ops_server import make_github_request, commit_files, delete_files


class TestMakeGithubRequest:
    """Test the make_github_request helper function."""
    
    @patch('github_file_ops_server.requests.request')
    def test_successful_request(self, mock_request):
        """Test successful GitHub API request."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = '{"key": "value"}'
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response
        
        result = make_github_request("GET", "https://api.github.com/test", "token123")
        
        assert result == {"key": "value"}
        mock_request.assert_called_once_with(
            method="GET",
            url="https://api.github.com/test",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer token123",
                "X-GitHub-Api-Version": "2022-11-28"
            },
            json=None
        )
    
    @patch('github_file_ops_server.requests.request')
    def test_failed_request(self, mock_request):
        """Test failed GitHub API request."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response
        
        with pytest.raises(Exception, match="GitHub API error: 404 Not Found"):
            make_github_request("GET", "https://api.github.com/test", "token123")


class TestCommitFiles:
    """Test the commit_files function."""
    
    @patch('github_file_ops_server.make_github_request')
    def test_successful_commit(self, mock_github_request):
        """Test successful file commit."""
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
        
        result = commit_files(
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
        assert "2 file(s)" in result["message"]
        
        # Verify the tree creation call
        tree_call = mock_github_request.call_args_list[2]
        assert tree_call[0][0] == "POST"
        assert "git/trees" in tree_call[0][1]
        tree_data = tree_call[0][3]
        assert tree_data["base_tree"] == "tree123"
        assert len(tree_data["tree"]) == 2
        assert tree_data["tree"][0]["path"] == "test.txt"
        assert tree_data["tree"][0]["content"] == "Hello World"
    
    @patch('github_file_ops_server.make_github_request')
    def test_commit_failure(self, mock_github_request):
        """Test commit failure handling."""
        mock_github_request.side_effect = Exception("API Error")
        
        result = commit_files(
            message="Test commit",
            files=[{"path": "test.txt", "content": "Hello"}],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "API Error" in result["error"]


class TestDeleteFiles:
    """Test the delete_files function."""
    
    @patch('github_file_ops_server.make_github_request')
    def test_successful_delete(self, mock_github_request):
        """Test successful file deletion."""
        # Mock the API responses in order
        mock_github_request.side_effect = [
            # Get branch reference
            {"object": {"sha": "base123"}},
            # Get base commit
            {"tree": {"sha": "tree123"}},
            # Get current tree
            {
                "tree": [
                    {"path": "keep.txt", "mode": "100644", "type": "blob", "sha": "sha1"},
                    {"path": "delete.txt", "mode": "100644", "type": "blob", "sha": "sha2"},
                    {"path": "also-delete.txt", "mode": "100644", "type": "blob", "sha": "sha3"}
                ]
            },
            # Create new tree
            {"sha": "newtree123"},
            # Create commit
            {"sha": "newcommit123", "html_url": "https://github.com/owner/repo/commit/newcommit123"},
            # Update reference
            {"ref": "refs/heads/main"}
        ]
        
        result = delete_files(
            message="Delete files",
            paths=["delete.txt", "also-delete.txt"],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is True
        assert result["sha"] == "newcommit123"
        assert "2 file(s)" in result["message"]
        
        # Verify the new tree only contains the kept file
        tree_call = mock_github_request.call_args_list[3]
        assert tree_call[0][0] == "POST"
        assert "git/trees" in tree_call[0][1]
        tree_data = tree_call[0][3]
        assert len(tree_data["tree"]) == 1
        assert tree_data["tree"][0]["path"] == "keep.txt"
    
    @patch('github_file_ops_server.make_github_request')
    def test_delete_nonexistent_files(self, mock_github_request):
        """Test deleting files that don't exist."""
        # Mock the API responses
        mock_github_request.side_effect = [
            # Get branch reference
            {"object": {"sha": "base123"}},
            # Get base commit
            {"tree": {"sha": "tree123"}},
            # Get current tree (no files match the delete paths)
            {
                "tree": [
                    {"path": "keep1.txt", "mode": "100644", "type": "blob", "sha": "sha1"},
                    {"path": "keep2.txt", "mode": "100644", "type": "blob", "sha": "sha2"}
                ]
            },
            # Create new tree
            {"sha": "newtree123"},
            # Create commit
            {"sha": "newcommit123", "html_url": "https://github.com/owner/repo/commit/newcommit123"},
            # Update reference
            {"ref": "refs/heads/main"}
        ]
        
        result = delete_files(
            message="Delete files",
            paths=["nonexistent.txt"],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is True
        assert "0 file(s)" in result["message"]
    
    @patch('github_file_ops_server.make_github_request')
    def test_delete_failure(self, mock_github_request):
        """Test delete failure handling."""
        mock_github_request.side_effect = Exception("API Error")
        
        result = delete_files(
            message="Delete files",
            paths=["test.txt"],
            owner="testowner",
            repo="testrepo",
            branch="main",
            github_token="token123"
        )
        
        assert result["success"] is False
        assert "API Error" in result["error"]