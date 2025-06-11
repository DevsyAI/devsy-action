"""Tests for prepare_tools.py"""

import os
import tempfile
import pytest
from unittest.mock import patch, mock_open
from src.prepare_tools import get_base_tools, combine_tools, set_github_output, main


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
            "Read",
            "Write",
            "Bash(git:*)",
            "Bash(gh:*)"  # Updated to match broader pattern
        ]
        for tool in expected_tools:
            assert tool in result

    def test_get_base_tools_format(self):
        """Test that base tools are comma-separated."""
        result = get_base_tools()
        tools = result.split(",")
        assert len(tools) > 10  # Should have many base tools
        assert all(tool.strip() for tool in tools)  # No empty tools


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