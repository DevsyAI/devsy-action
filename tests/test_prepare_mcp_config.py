"""Tests for prepare_mcp_config.py script."""

import json
import os
import pytest
from unittest.mock import patch, mock_open
import responses

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from prepare_mcp_config import generate_mcp_config, set_github_output, main


class TestGenerateMcpConfig:
    """Test the generate_mcp_config function."""
    
    def test_pr_update_mode(self):
        """Test MCP config generation for pr-update mode."""
        with patch.dict(os.environ, {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_REF_NAME": "feature-branch",
            "GITHUB_ACTION_PATH": "/path/to/action"
        }, clear=True):
            config_json = generate_mcp_config("pr-update", "token123")
            config = json.loads(config_json)
            
            assert "mcpServers" in config
            assert "github-file-ops" in config["mcpServers"]
            
            server_config = config["mcpServers"]["github-file-ops"]
            assert server_config["command"] == "/tmp/devsy-action-env/bin/python"
            assert server_config["args"][0] == "/path/to/action/src/mcp/github_file_ops_server.py"
            assert server_config["env"]["GITHUB_TOKEN"] == "token123"
            assert server_config["env"]["REPO_OWNER"] == "owner"
            assert server_config["env"]["REPO_NAME"] == "repo"
            assert server_config["env"]["BRANCH_NAME"] == "feature-branch"
    
    def test_pr_gen_mode(self):
        """Test MCP config generation for pr-gen mode."""
        with patch.dict(os.environ, {
            "GITHUB_REPOSITORY": "DevsyAI/devsy-action",
            "GITHUB_REF_NAME": "feat/mcp-tools-for-pr-gen",
            "GITHUB_ACTION_PATH": "/tmp/devsy-action-env"
        }, clear=True):
            config_json = generate_mcp_config("pr-gen", "token123")
            config = json.loads(config_json)
            
            assert "mcpServers" in config
            assert "github-file-ops" in config["mcpServers"]
            
            server_config = config["mcpServers"]["github-file-ops"]
            assert server_config["command"] == "/tmp/devsy-action-env/bin/python"
            assert server_config["args"][0] == "/tmp/devsy-action-env/src/mcp/github_file_ops_server.py"
            assert server_config["env"]["GITHUB_TOKEN"] == "token123"
            assert server_config["env"]["REPO_OWNER"] == "DevsyAI"
            assert server_config["env"]["REPO_NAME"] == "devsy-action"
            assert server_config["env"]["BRANCH_NAME"] == "feat/mcp-tools-for-pr-gen"
    
    def test_plan_gen_mode(self):
        """Test MCP config generation for plan-gen mode."""
        config_json = generate_mcp_config("plan-gen", "token123")
        assert config_json == '{"mcpServers": {}}'
    
    def test_invalid_repository(self):
        """Test handling of invalid repository format."""
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "invalid"}):
            config_json = generate_mcp_config("pr-update", "token123")
            assert config_json == '{"mcpServers": {}}'
    
    def test_missing_repository(self):
        """Test handling of missing repository."""
        with patch.dict(os.environ, {}, clear=True):
            config_json = generate_mcp_config("pr-update", "token123")
            assert config_json == '{"mcpServers": {}}'
    
    def test_head_ref_priority(self):
        """Test that GITHUB_HEAD_REF takes priority over GITHUB_REF_NAME."""
        with patch.dict(os.environ, {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_HEAD_REF": "pr-branch",
            "GITHUB_REF_NAME": "main",
            "GITHUB_ACTION_PATH": "/path"
        }, clear=True):
            config_json = generate_mcp_config("pr-update", "token123")
            config = json.loads(config_json)
            assert config["mcpServers"]["github-file-ops"]["env"]["BRANCH_NAME"] == "pr-branch"
    
    @responses.activate
    def test_pr_update_with_pr_number(self):
        """Test MCP config generation for pr-update mode with PR number."""
        # Mock GitHub API response
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/pulls/123",
            json={"head": {"ref": "feature-branch-from-pr"}, "base": {"ref": "main"}},
            status=200
        )
        
        with patch.dict(os.environ, {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_REF_NAME": "main",
            "GITHUB_ACTION_PATH": "/path"
        }, clear=True):
            config_json = generate_mcp_config("pr-update", "token123", "123")
            config = json.loads(config_json)
            assert config["mcpServers"]["github-file-ops"]["env"]["BRANCH_NAME"] == "feature-branch-from-pr"


class TestSetGithubOutput:
    """Test the set_github_output function."""
    
    def test_with_github_output_json(self):
        """Test setting output with JSON value."""
        with patch.dict(os.environ, {"GITHUB_OUTPUT": "/tmp/output"}):
            with patch("builtins.open", mock_open()) as mock_file:
                set_github_output("mcp_config", '{"test": "value"}')
                mock_file.assert_called_once_with("/tmp/output", "a", encoding="utf-8")
                mock_file().write.assert_called_once_with('mcp_config={"test": "value"}\n')
    
    def test_with_github_output_string(self):
        """Test setting output with string value."""
        with patch.dict(os.environ, {"GITHUB_OUTPUT": "/tmp/output"}):
            with patch("builtins.open", mock_open()) as mock_file:
                set_github_output("key", "value")
                mock_file().write.assert_called_once_with("key=value\n")
    
    def test_without_github_output(self, capsys):
        """Test local testing mode without GITHUB_OUTPUT."""
        with patch.dict(os.environ, {}, clear=True):
            set_github_output("key", "value")
            captured = capsys.readouterr()
            assert captured.out == "key=value\n"


class TestMain:
    """Test the main function."""
    
    @responses.activate
    def test_successful_pr_update(self, capsys):
        """Test successful execution for pr-update mode."""
        # Mock GitHub API response
        responses.add(
            responses.GET,
            "https://api.github.com/repos/owner/repo/pulls/456",
            json={"head": {"ref": "pr-feature-branch"}, "base": {"ref": "main"}},
            status=200
        )
        
        with patch.dict(os.environ, {
            "DEVSY_MODE": "pr-update",
            "GITHUB_TOKEN": "token123",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_ACTION_PATH": "/action",
            "DEVSY_PR_NUMBER": "456"
        }):
            with patch("prepare_mcp_config.set_github_output") as mock_output:
                main()
                
                # Verify output was set
                mock_output.assert_called_once()
                args = mock_output.call_args[0]
                assert args[0] == "mcp_config"
                assert "github-file-ops" in args[1]
                
                # Check console output
                captured = capsys.readouterr()
                assert "✅ MCP configuration prepared for pr-update mode" in captured.out
                assert "🔧 GitHub file operations server enabled" in captured.out
    
    def test_successful_pr_gen(self, capsys):
        """Test successful execution for pr-gen mode."""
        with patch.dict(os.environ, {
            "DEVSY_MODE": "pr-gen",
            "GITHUB_TOKEN": "token123",
            "GITHUB_REPOSITORY": "DevsyAI/devsy-action",
            "GITHUB_ACTION_PATH": "/tmp/devsy-action-env",
            "GITHUB_REF_NAME": "feat/mcp-tools-for-pr-gen"
        }):
            with patch("prepare_mcp_config.set_github_output") as mock_output:
                main()
                
                # Verify MCP config was set (should now include github-file-ops)
                mock_output.assert_called_once()
                args = mock_output.call_args[0]
                assert args[0] == "mcp_config"
                assert "github-file-ops" in args[1]
                
                # Check console output
                captured = capsys.readouterr()
                assert "✅ MCP configuration prepared for pr-gen mode" in captured.out
                assert "🔧 GitHub file operations server enabled" in captured.out
    
    def test_missing_mode(self, capsys):
        """Test error when DEVSY_MODE is missing."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "token123"}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "❌ DEVSY_MODE environment variable not set" in captured.out
    
    def test_missing_token(self, capsys):
        """Test error when GITHUB_TOKEN is missing."""
        with patch.dict(os.environ, {"DEVSY_MODE": "pr-update"}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "❌ GITHUB_TOKEN environment variable not set" in captured.out