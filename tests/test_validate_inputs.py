"""Tests for validate_inputs.py"""

import pytest
import sys
from unittest.mock import patch
from src.validate_inputs import validate_mode, validate_authentication, validate_mode_requirements, main


class TestValidateMode:
    """Test mode validation."""

    def test_valid_modes(self):
        """Test that valid modes pass validation."""
        valid_modes = ["pr-gen", "pr-update", "plan-gen"]
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

    def test_plan_gen_mode(self):
        """Test plan-gen mode doesn't require additional parameters."""
        # Should not raise any exception
        validate_mode_requirements("plan-gen", "", "", "")


class TestMain:
    """Test main function integration."""

    @patch('sys.argv', ['validate_inputs.py', '--mode', 'pr-gen', '--prompt', 'test'])
    def test_main_success(self, capsys):
        """Test successful validation."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code is None  # Normal exit
        
        captured = capsys.readouterr()
        assert "✅ All input validations passed" in captured.out

    @patch('sys.argv', ['validate_inputs.py', '--mode', 'invalid'])
    def test_main_failure(self):
        """Test validation failure."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch('sys.argv', [
        'validate_inputs.py',
        '--mode', 'pr-gen',
        '--anthropic-api-key', 'sk-ant-123',
        '--prompt', 'test prompt'
    ])
    def test_main_full_args(self, capsys):
        """Test main with full arguments."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code is None
        
        captured = capsys.readouterr()
        assert "✅ All input validations passed" in captured.out

    @patch('sys.argv', [
        'validate_inputs.py',
        '--mode', 'pr-update',
        '--anthropic-api-key', 'sk-ant-123',
        '--pr-number', '456'
    ])
    def test_main_pr_update(self, capsys):
        """Test main with pr-update mode."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code is None
        
        captured = capsys.readouterr()
        assert "✅ All input validations passed" in captured.out

    @patch('sys.argv', [
        'validate_inputs.py',
        '--mode', 'plan-gen',
        '--use-bedrock', 'true'
    ])
    def test_main_bedrock_auth(self, capsys):
        """Test main with Bedrock authentication."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code is None
        
        captured = capsys.readouterr()
        assert "✅ All input validations passed" in captured.out