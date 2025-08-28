"""Tests for prepare_tools.py"""

import os
import tempfile
from unittest.mock import mock_open, patch

import pytest
from src.prepare_tools import (
    combine_tools,
    generate_claude_args,
    generate_settings_json,
    get_base_tools,
    get_default_disallowed_tools,
    main,
    set_github_output,
)


class TestGetBaseTools:
    """Test getting base tools."""

    def test_get_base_tools_returns_string(self):
        """Test that get_base_tools returns a string."""
        result = get_base_tools()
        assert isinstance(result, str)

    def test_get_base_tools_contains_expected_tools(self):
        """Test that base tools contain expected tools."""
        result = get_base_tools()
        expected_tools = [
            "Edit",
            "MultiEdit",
            "Read",
            "Write",
            "Bash(git:*)",
            "Bash(gh pr:*)",  # Updated to match PR-specific pattern
            "Bash(gh auth:status)",
            "Bash(find:*)",  # Find commands for file searching
            "Bash(mv:*)"     # Move/rename commands
        ]
        for tool in expected_tools:
            assert tool in result

    def test_get_base_tools_format(self):
        """Test that base tools are comma-separated."""
        result = get_base_tools()
        tools = result.split(",")
        assert len(tools) >= 16  # Should have many base tools (added mv)
        assert all(tool.strip() for tool in tools)  # No empty tools

    def test_get_base_tools_pr_update_mode_includes_mcp_tools(self):
        """Test that pr-update mode includes MCP GitHub file operations tools."""
        result = get_base_tools("pr-update")
        assert "mcp__github-file-ops__push_changes" in result

    def test_get_base_tools_pr_gen_mode_includes_mcp_tools(self):
        """Test that pr-gen mode includes MCP GitHub file operations tools."""
        result = get_base_tools("pr-gen")
        assert "mcp__github-file-ops__push_changes" in result

    def test_get_base_tools_pr_update_mode_excludes_removed_tools(self):
        """Test that pr-update mode does not include removed MCP tools."""
        result = get_base_tools("pr-update")
        assert "mcp__github-file-ops__commit_files" not in result
        assert "mcp__github-file-ops__delete_files" not in result

    def test_get_base_tools_other_modes_exclude_mcp_tools(self):
        """Test that plan-gen and None modes do not include MCP GitHub file operations tools."""
        for mode in ["plan-gen", None]:
            result = get_base_tools(mode)
            assert "mcp__github-file-ops__push_changes" not in result


class TestGetDefaultDisallowedTools:
    """Test getting default disallowed tools."""

    def test_get_default_disallowed_tools_returns_string(self):
        """Test that get_default_disallowed_tools returns a string."""
        result = get_default_disallowed_tools()
        assert isinstance(result, str)

    def test_get_default_disallowed_tools_contains_expected_tools(self):
        """Test that default disallowed tools contain WebFetch and WebSearch."""
        result = get_default_disallowed_tools()
        assert "WebFetch" in result
        assert "WebSearch" in result

    def test_get_default_disallowed_tools_format(self):
        """Test that default disallowed tools are comma-separated."""
        result = get_default_disallowed_tools()
        tools = result.split(",")
        assert len(tools) == 2
        assert all(tool.strip() for tool in tools)


class TestCombineTools:
    """Test combining tools."""

    def test_combine_tools_with_additional(self):
        """Test combining base tools with additional tools."""
        base = "Edit,Read,Write"
        additional = "WebSearch,CustomTool"
        result = combine_tools(base, additional)
        assert result == "Edit,Read,Write,WebSearch,CustomTool"

    def test_combine_tools_no_additional(self):
        """Test combining with empty additional tools."""
        base = "Edit,Read,Write"
        additional = ""
        result = combine_tools(base, additional)
        assert result == base

    def test_combine_tools_whitespace_additional(self):
        """Test combining with whitespace-only additional tools."""
        base = "Edit,Read,Write"
        additional = "   "
        result = combine_tools(base, additional)
        assert result == base


class TestSetGithubOutput:
    """Test setting GitHub output."""

    def test_set_github_output_with_file(self, tmp_path):
        """Test setting output when GITHUB_OUTPUT file exists."""
        output_file = tmp_path / "github_output"
        output_file.write_text("")

        with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output_file)}):
            set_github_output("test_key", "test_value")

        content = output_file.read_text()
        assert "test_key=test_value\n" in content

    def test_set_github_output_no_file(self, capsys):
        """Test setting output when no GITHUB_OUTPUT file."""
        with patch.dict(os.environ, {}, clear=True):
            set_github_output("test_key", "test_value")

        captured = capsys.readouterr()
        assert "test_key=test_value" in captured.out

    def test_set_github_output_multiple_calls(self, tmp_path):
        """Test multiple calls to set_github_output."""
        output_file = tmp_path / "github_output"
        output_file.write_text("")

        with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output_file)}):
            set_github_output("key1", "value1")
            set_github_output("key2", "value2")

        content = output_file.read_text()
        assert "key1=value1\n" in content
        assert "key2=value2\n" in content


# Main function integration tests removed - covered by manual testing


class TestGenerateSettingsJson:
    """Test generating settings JSON."""

    def test_generate_settings_json_empty(self):
        """Test generating settings JSON with no parameters."""
        result = generate_settings_json("pr-gen", "", "")
        assert result == ""

    def test_generate_settings_json_with_model(self):
        """Test generating settings JSON with model."""
        result = generate_settings_json("pr-gen", "", "", model="claude-4")
        expected = {"model": "claude-4"}
        assert result == '{"model": "claude-4"}'

    def test_generate_settings_json_with_tools(self):
        """Test generating settings JSON with tools."""
        result = generate_settings_json("pr-gen", "Edit,Read", "WebFetch,WebSearch")
        import json
        parsed = json.loads(result)
        assert parsed["permissions"]["allow"] == ["Edit", "Read"]
        assert parsed["permissions"]["deny"] == ["WebFetch", "WebSearch"]

    def test_generate_settings_json_with_env(self):
        """Test generating settings JSON with environment variables."""
        result = generate_settings_json("pr-gen", "", "", claude_env="NODE_ENV=test,DEBUG=true")
        import json
        parsed = json.loads(result)
        assert parsed["env"]["NODE_ENV"] == "test"
        assert parsed["env"]["DEBUG"] == "true"

    def test_generate_settings_json_with_all_params(self):
        """Test generating settings JSON with all parameters."""
        result = generate_settings_json(
            mode="pr-gen",
            allowed_tools="Edit,Read", 
            disallowed_tools="WebFetch",
            model="claude-4",
            max_turns="100",
            timeout_minutes="30",
            claude_env="DEBUG=true",
            system_prompt="You are helpful"
        )
        import json
        parsed = json.loads(result)
        assert parsed["model"] == "claude-4"
        assert parsed["systemPrompt"] == "You are helpful"
        assert parsed["maxTurns"] == 100
        assert parsed["timeoutMinutes"] == 30
        assert parsed["env"]["DEBUG"] == "true"
        assert parsed["permissions"]["allow"] == ["Edit", "Read"]
        assert parsed["permissions"]["deny"] == ["WebFetch"]


class TestGenerateClaudeArgs:
    """Test generating claude_args."""

    def test_generate_claude_args_empty(self):
        """Test generating claude_args with no parameters."""
        result = generate_claude_args()
        assert result == ""

    def test_generate_claude_args_with_mcp_config(self):
        """Test generating claude_args with MCP config."""
        result = generate_claude_args(mcp_config="/tmp/mcp-config.json")
        assert result == "--mcp-config /tmp/mcp-config.json"

    def test_generate_claude_args_with_empty_mcp_config(self):
        """Test generating claude_args with empty MCP config."""
        result = generate_claude_args(mcp_config="")
        assert result == ""


class TestMainFunction:
    """Test main function integration."""

    @patch('src.prepare_tools.set_github_output')
    def test_main_with_default_tools(self, mock_set_output):
        """Test that main function generates settings and claude_args outputs."""
        import sys

        test_args = ['prepare_tools.py']

        with patch.object(sys, 'argv', test_args):
            main()

        # Check that set_github_output was called with settings and claude_args
        calls = mock_set_output.call_args_list
        settings_call = [call for call in calls if call[0][0] == 'settings'][0]
        claude_args_call = [call for call in calls if call[0][0] == 'claude_args'][0]

        # Settings should contain permissions with default disallowed tools
        import json
        settings = json.loads(settings_call[0][1])
        assert "WebFetch" in settings["permissions"]["deny"]
        assert "WebSearch" in settings["permissions"]["deny"]

    @patch('src.prepare_tools.set_github_output')
    def test_main_combines_user_disallowed_tools(self, mock_set_output):
        """Test that main function combines default and user disallowed tools."""
        import sys

        test_args = ['prepare_tools.py', '--disallowed-tools', 'CustomTool,AnotherTool']

        with patch.object(sys, 'argv', test_args):
            main()

        # Check that set_github_output was called with settings
        calls = mock_set_output.call_args_list
        settings_call = [call for call in calls if call[0][0] == 'settings'][0]

        # Should contain default tools plus user tools
        import json
        settings = json.loads(settings_call[0][1])
        denied_tools = settings["permissions"]["deny"]
        assert "WebFetch" in denied_tools
        assert "WebSearch" in denied_tools
        assert "CustomTool" in denied_tools
        assert "AnotherTool" in denied_tools
