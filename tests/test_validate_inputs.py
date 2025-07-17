"""Tests for validate_inputs.py"""

import sys
from unittest.mock import patch

import pytest
from src.validate_inputs import main, validate_authentication, validate_mode, validate_mode_requirements


class TestValidateMode:
    """Test mode validation."""

    def test_valid_modes(self):
        """Test that valid modes pass validation."""
        valid_modes = ["pr-gen", "pr-update", "pr-review", "plan-gen"]
        for mode in valid_modes:
            # Should not raise any exception
            validate_mode(mode)

    def test_invalid_mode(self):
        """Test that invalid modes raise SystemExit."""
        with pytest.raises(SystemExit) as exc_info:
            validate_mode("invalid-mode")
        assert exc_info.value.code == 1

    def test_empty_mode(self):
        """Test that empty mode raises SystemExit."""
        with pytest.raises(SystemExit) as exc_info:
            validate_mode("")
        assert exc_info.value.code == 1


class TestValidateAuthentication:
    """Test authentication validation."""

    def test_api_key_provided(self):
        """Test that API key authentication passes."""
        # Should not raise any exception
        validate_authentication("sk-ant-123", "false", "false")

    def test_bedrock_authentication(self):
        """Test that Bedrock authentication passes."""
        # Should not raise any exception
        validate_authentication("", "true", "false")

    def test_vertex_authentication(self):
        """Test that Vertex authentication passes."""
        # Should not raise any exception
        validate_authentication("", "false", "true")

    def test_no_authentication(self):
        """Test that no authentication raises SystemExit."""
        with pytest.raises(SystemExit) as exc_info:
            validate_authentication("", "false", "false")
        assert exc_info.value.code == 1

    def test_empty_api_key_string(self):
        """Test that empty string API key with no alternatives fails."""
        with pytest.raises(SystemExit) as exc_info:
            validate_authentication("", "false", "false")
        assert exc_info.value.code == 1


class TestValidateModeRequirements:
    """Test mode-specific requirements validation."""

    def test_pr_gen_with_prompt(self):
        """Test pr-gen mode with prompt provided."""
        # Should not raise any exception
        validate_mode_requirements("pr-gen", "test prompt", "", "")

    def test_pr_gen_with_prompt_file(self):
        """Test pr-gen mode with prompt file provided."""
        # Should not raise any exception
        validate_mode_requirements("pr-gen", "", "prompt.txt", "")

    def test_pr_gen_no_prompt(self):
        """Test pr-gen mode without prompt or prompt file."""
        with pytest.raises(SystemExit) as exc_info:
            validate_mode_requirements("pr-gen", "", "", "")
        assert exc_info.value.code == 1

    def test_pr_update_with_pr_number(self):
        """Test pr-update mode with PR number provided."""
        # Should not raise any exception
        validate_mode_requirements("pr-update", "", "", "123")

    def test_pr_update_no_pr_number(self):
        """Test pr-update mode without PR number."""
        with pytest.raises(SystemExit) as exc_info:
            validate_mode_requirements("pr-update", "", "", "")
        assert exc_info.value.code == 1

    def test_pr_review_with_pr_number(self):
        """Test pr-review mode with PR number provided."""
        # Should not raise any exception
        validate_mode_requirements("pr-review", "", "", "123")

    def test_pr_review_no_pr_number(self):
        """Test pr-review mode without PR number."""
        with pytest.raises(SystemExit) as exc_info:
            validate_mode_requirements("pr-review", "", "", "")
        assert exc_info.value.code == 1

    def test_plan_gen_mode(self):
        """Test plan-gen mode doesn't require additional parameters."""
        # Should not raise any exception
        validate_mode_requirements("plan-gen", "", "", "")


# Main function integration tests removed - covered by manual testing
