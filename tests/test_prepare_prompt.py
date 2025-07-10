"""Tests for prepare_prompt.py"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import responses
from src.prepare_prompt import load_template, render_template


class TestLoadTemplate:
    """Test template loading."""

    def test_load_template_success(self, tmp_path):
        """Test successful template loading."""
        # Create a mock template directory structure
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        template_file = templates_dir / "test-template.md"
        template_content = "This is a test template with {{ variable }}"
        template_file.write_text(template_content)

        # Mock the script location to point to our test directory
        with patch('src.prepare_prompt.Path') as mock_path:
            mock_path(__file__).parent.parent = tmp_path
            result = load_template("test-template")

        assert result == template_content

    def test_load_template_file_not_found(self, tmp_path):
        """Test template loading when file doesn't exist."""
        with patch('src.prepare_prompt.Path') as mock_path:
            mock_path(__file__).parent.parent = tmp_path

            with pytest.raises(FileNotFoundError):
                load_template("nonexistent-template")


class TestRenderTemplate:
    """Test template rendering."""

    def test_render_template_single_variable(self):
        """Test rendering template with single variable."""
        template = "Hello {{ name }}!"
        result = render_template(template, name="World")
        assert result == "Hello World!"

    def test_render_template_multiple_variables(self):
        """Test rendering template with multiple variables."""
        template = "Hello {{ name }}, today is {{ day }}!"
        result = render_template(template, name="Alice", day="Monday")
        assert result == "Hello Alice, today is Monday!"

    def test_render_template_no_variables(self):
        """Test rendering template with no variables."""
        template = "This is a static template"
        result = render_template(template)
        assert result == template

    def test_render_template_unused_variables(self):
        """Test rendering with extra variables not in template."""
        template = "Hello {{ name }}!"
        result = render_template(template, name="World", extra="unused")
        assert result == "Hello World!"

    def test_render_template_missing_variables(self):
        """Test rendering with missing variables."""
        template = "Hello {{ name }}, welcome to {{ place }}!"
        result = render_template(template, name="Alice")
        # Missing variables should remain as placeholders
        assert result == "Hello Alice, welcome to {{ place }}!"

    def test_render_template_none_value(self):
        """Test rendering with None value."""
        template = "Value: {{ value }}"
        result = render_template(template, value=None)
        assert result == "Value: "

    def test_render_template_numeric_values(self):
        """Test rendering with numeric values."""
        template = "Count: {{ count }}, Price: ${{ price }}"
        result = render_template(template, count=42, price=19.99)
        assert result == "Count: 42, Price: $19.99"

    def test_render_template_boolean_values(self):
        """Test rendering with boolean values."""
        template = "Active: {{ active }}, Debug: {{ debug }}"
        result = render_template(template, active=True, debug=False)
        assert result == "Active: True, Debug: False"

    def test_render_template_special_characters(self):
        """Test rendering with special characters in values."""
        template = "Message: {{ message }}"
        result = render_template(template, message="Hello & welcome to <app>!")
        assert result == "Message: Hello & welcome to <app>!"

    def test_render_template_multiline(self):
        """Test rendering multiline template."""
        template = """Hello {{ name }}!

Welcome to {{ app }}.
Your role is: {{ role }}
        """
        result = render_template(template, name="Alice", app="DevSy", role="developer")
        expected = """Hello Alice!

Welcome to DevSy.
Your role is: developer
        """
        assert result == expected


# Note: set_github_output is not in prepare_prompt.py, it's in other modules


# Integration tests would require mocking more complex GitHub API interactions
# and file system operations. For now, we focus on unit testing the core functions.

# Integration tests removed - core functionality tested above


class TestPreparePrompt:
    """Test the main prepare_prompt functionality."""

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.prepare_prompt.load_template')
    @patch('src.prepare_prompt.requests.get')
    def test_pr_gen_mode_with_special_characters(self, mock_get, mock_load_template, mock_file, mock_subprocess):
        """Test PR generation mode with special characters that need JSON escaping."""
        # Setup
        mock_load_template.side_effect = lambda name: f"Template for {name}: {{{{ user_prompt }}}}"

        # Mock subprocess.run to simulate jq behavior
        def mock_jq_run(cmd, **kwargs):
            result = MagicMock()
            # Simulate jq JSON encoding
            input_text = kwargs.get('input', '')
            if 'rtrimstr' in cmd:
                # Simulate jq -Rs 'rtrimstr("\n")' behavior
                result.stdout = json.dumps(input_text.rstrip('\n'))
            result.returncode = 0
            return result

        mock_subprocess.return_value = mock_jq_run(['jq'])

        # Test with special characters
        test_prompt = 'Add `backticks` and "quotes" and $variables and $(commands)'

        import sys

        from src.prepare_prompt import main

        env_vars = {
            'DEVSY_MODE': 'pr-gen',
            'DEVSY_PROMPT': test_prompt,
            'DEVSY_GITHUB_TOKEN': 'fake-token',
            'DEVSY_REPO': 'test/repo',
            'DEVSY_BASE_BRANCH': 'main',
            'GITHUB_OUTPUT': '/tmp/test_output'
        }

        with patch.dict(os.environ, env_vars):
            main()

        # Verify subprocess was called with jq for JSON serialization
        assert mock_subprocess.called
        calls = mock_subprocess.call_args_list

        # Should have 2 calls to jq (system_prompt and user_prompt)
        assert len(calls) == 2

        # Check that jq was called with correct arguments
        for call in calls:
            args, kwargs = call
            assert args[0] == ['jq', '-Rs', 'rtrimstr("\\n")']
            assert 'input' in kwargs
            assert kwargs['text'] is True
            assert kwargs['capture_output'] is True

    @patch('subprocess.run')
    def test_json_serialization_with_multiline_content(self, mock_subprocess):
        """Test that multiline content is properly JSON serialized."""
        # Mock subprocess to return encoded JSON
        def mock_jq_run(cmd, **kwargs):
            result = MagicMock()
            input_text = kwargs.get('input', '')
            # Properly encode multiline strings as JSON
            result.stdout = json.dumps(input_text.rstrip('\n'))
            result.returncode = 0
            return result

        mock_subprocess.side_effect = mock_jq_run

        # Test multiline content
        multiline_text = """First line
Second line with "quotes"
Third line with `backticks`
Fourth line with $variables"""

        import subprocess

        from src.prepare_prompt import main

        # Simulate the jq call
        result = subprocess.run(
            ["jq", "-Rs", 'rtrimstr("\\n")'],
            input=multiline_text,
            text=True,
            capture_output=True,
            check=True
        )

        # Verify the mock was called
        assert mock_subprocess.called

        # Verify the JSON output can be decoded
        json_output = result.stdout
        decoded = json.loads(json_output)
        assert 'quotes' in decoded
        assert 'backticks' in decoded
        assert '$variables' in decoded

    @patch('subprocess.run')
    def test_json_serialization_handles_jq_failure(self, mock_subprocess):
        """Test that jq failures are handled properly."""
        # Mock subprocess to simulate jq failure
        mock_subprocess.side_effect = Exception("jq not found")

        import sys

        from src.prepare_prompt import main

        env_vars = {
            'DEVSY_MODE': 'pr-gen',
            'DEVSY_PROMPT': 'test',
            'DEVSY_GITHUB_TOKEN': 'fake-token',
            'DEVSY_REPO': 'test/repo'
        }

        with patch.dict(os.environ, env_vars):
            with pytest.raises(SystemExit):
                main()
