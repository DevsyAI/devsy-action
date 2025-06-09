"""Tests for prepare_prompt.py"""

import json
import pytest
import responses
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
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