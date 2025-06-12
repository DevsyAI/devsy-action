"""Tests for prepare_tools.py"""

import os
import tempfile
import pytest
from unittest.mock import patch, mock_open
from src.prepare_tools import get_base_tools, get_default_disallowed_tools, combine_tools, set_github_output, main


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
            "Bash(gh pr:*)"  # Updated to match PR-specific pattern
        ]
        for tool in expected_tools:
            assert tool in result

    def test_get_base_tools_format(self):
        """Test that base tools are comma-separated."""
        result = get_base_tools()
        tools = result.split(",")
        assert len(tools) > 10  # Should have many base tools
        assert all(tool.strip() for tool in tools)  # No empty tools


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


class TestMainFunction:
    """Test main function integration."""
    
    @patch('src.prepare_tools.set_github_output')
    def test_main_with_default_disallowed_tools(self, mock_set_output):
        """Test that main function includes default disallowed tools."""
        import sys
        from src.prepare_tools import main
        
        test_args = ['prepare_tools.py']
        
        with patch.object(sys, 'argv', test_args):
            main()
        
        # Check that set_github_output was called with default disallowed tools
        calls = mock_set_output.call_args_list
        disallowed_call = [call for call in calls if call[0][0] == 'disallowed_tools'][0]
        
        # Should contain WebFetch and WebSearch
        assert disallowed_call[0][1] == "WebFetch,WebSearch"
    
    @patch('src.prepare_tools.set_github_output')
    def test_main_combines_user_disallowed_tools(self, mock_set_output):
        """Test that main function combines default and user disallowed tools."""
        import sys
        from src.prepare_tools import main
        
        test_args = ['prepare_tools.py', '--disallowed-tools', 'CustomTool,AnotherTool']
        
        with patch.object(sys, 'argv', test_args):
            main()
        
        # Check that set_github_output was called with combined disallowed tools
        calls = mock_set_output.call_args_list
        disallowed_call = [call for call in calls if call[0][0] == 'disallowed_tools'][0]
        
        # Should contain default tools plus user tools
        assert "WebFetch" in disallowed_call[0][1]
        assert "WebSearch" in disallowed_call[0][1]
        assert "CustomTool" in disallowed_call[0][1]
        assert "AnotherTool" in disallowed_call[0][1]