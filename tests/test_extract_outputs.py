"""Tests for extract_outputs.py"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from src.extract_outputs import (
    extract_github_urls,
    extract_pr_numbers,
    extract_branch_names,
    extract_plan_content,
    parse_execution_file,
    main
)


class TestExtractGithubUrls:
    """Test GitHub URL extraction."""

    def test_extract_pr_urls(self):
        """Test extracting PR URLs."""
        text = "Created PR at https://github.com/owner/repo/pull/123"
        urls = extract_github_urls(text)
        assert "https://github.com/owner/repo/pull/123" in urls

    def test_extract_issue_urls(self):
        """Test extracting issue URLs."""
        text = "Related to https://github.com/owner/repo/issues/456"
        urls = extract_github_urls(text)
        assert "https://github.com/owner/repo/issues/456" in urls

    def test_extract_commit_urls(self):
        """Test extracting commit URLs."""
        text = "See commit https://github.com/owner/repo/commit/789"
        urls = extract_github_urls(text)
        assert "https://github.com/owner/repo/commit/789" in urls

    def test_extract_multiple_urls(self):
        """Test extracting multiple GitHub URLs."""
        text = """
        Created PR: https://github.com/owner/repo/pull/123
        Related issue: https://github.com/owner/repo/issues/456
        """
        urls = extract_github_urls(text)
        assert len(urls) == 2
        assert "https://github.com/owner/repo/pull/123" in urls
        assert "https://github.com/owner/repo/issues/456" in urls

    def test_extract_no_urls(self):
        """Test text with no GitHub URLs."""
        text = "This is just regular text with no GitHub links"
        urls = extract_github_urls(text)
        assert len(urls) == 0

    def test_extract_invalid_github_urls(self):
        """Test that invalid GitHub URLs are not extracted."""
        text = "https://github.com/owner/invalid-url and https://example.com/not-github"
        urls = extract_github_urls(text)
        assert len(urls) == 0


class TestExtractPrNumbers:
    """Test PR number extraction."""

    def test_extract_pr_hash_format(self):
        """Test extracting PR numbers in #123 format."""
        text = "Created PR #123"
        numbers = extract_pr_numbers(text)
        assert 123 in numbers

    def test_extract_pr_with_prefix(self):
        """Test extracting PR numbers with PR prefix."""
        text = "See PR #456 for details"
        numbers = extract_pr_numbers(text)
        assert 456 in numbers

    def test_extract_pull_request_format(self):
        """Test extracting with 'pull request' format."""
        text = "Created pull request #789"
        numbers = extract_pr_numbers(text)
        assert 789 in numbers

    def test_extract_from_url(self):
        """Test extracting PR numbers from URLs."""
        text = "https://github.com/owner/repo/pull/321"
        numbers = extract_pr_numbers(text)
        assert 321 in numbers

    def test_extract_multiple_pr_numbers(self):
        """Test extracting multiple PR numbers."""
        text = "Related to PR #123 and pull request #456"
        numbers = extract_pr_numbers(text)
        assert 123 in numbers
        assert 456 in numbers

    def test_extract_case_insensitive(self):
        """Test case insensitive extraction."""
        text = "pr #123 and PULL REQUEST #456"
        numbers = extract_pr_numbers(text)
        assert 123 in numbers
        assert 456 in numbers

    def test_extract_no_pr_numbers(self):
        """Test text with no PR numbers."""
        text = "This text has no PR references"
        numbers = extract_pr_numbers(text)
        assert len(numbers) == 0

    def test_extract_invalid_numbers(self):
        """Test handling of invalid number formats."""
        text = "PR #abc and PR #"
        numbers = extract_pr_numbers(text)
        assert len(numbers) == 0


class TestExtractBranchNames:
    """Test branch name extraction."""

    def test_extract_feature_branch(self):
        """Test extracting feature branch names."""
        text = "Created branch feature/new-feature"
        branches = extract_branch_names(text)
        assert "feature/new-feature" in branches

    def test_extract_fix_branch(self):
        """Test extracting fix branch names."""
        text = "Working on branch fix/bug-123"
        branches = extract_branch_names(text)
        assert "fix/bug-123" in branches

    def test_extract_from_git_output(self):
        """Test extracting from git command output."""
        text = "Switched to a new branch 'feature/auth-system'"
        branches = extract_branch_names(text)
        assert "feature/auth-system" in branches

    def test_extract_multiple_branches(self):
        """Test extracting multiple branch names."""
        text = "Merged feature/login into develop"
        branches = extract_branch_names(text)
        assert "feature/login" in branches
        assert "develop" in branches

    def test_extract_no_branches(self):
        """Test text with no branch references."""
        text = "This is regular text with no branch names"
        branches = extract_branch_names(text)
        assert len(branches) == 0


class TestExtractPlanContent:
    """Test plan content extraction."""

    def test_extract_plan_from_markdown(self):
        """Test extracting plan from markdown content."""
        text = """
# Implementation Plan

## Step 1: Setup
- Initialize project
- Configure dependencies

## Step 2: Development
- Implement features
- Add tests
        """
        plan = extract_plan_content(text)
        assert "Implementation Plan" in plan
        assert "Step 1: Setup" in plan
        assert "Step 2: Development" in plan

    def test_extract_plan_simple_format(self):
        """Test extracting plan in simple format."""
        text = """
Plan:
1. First step
2. Second step
3. Third step
        """
        plan = extract_plan_content(text)
        assert "Plan:" in plan
        assert "First step" in plan
        assert "Third step" in plan

    def test_extract_no_plan_content(self):
        """Test when no plan content is found."""
        text = "This is just regular output with no plan"
        plan = extract_plan_content(text)
        assert plan == ""

    def test_extract_plan_with_code_blocks(self):
        """Test extracting plan with code examples."""
        text = """
# Implementation Plan

## Database Setup
```sql
CREATE TABLE users (id INT, name VARCHAR(255));
```

## Next Steps
- Implement authentication
        """
        plan = extract_plan_content(text)
        assert "Implementation Plan" in plan
        assert "CREATE TABLE" in plan
        assert "Next Steps" in plan


class TestParseExecutionFile:
    """Test execution file parsing."""

    def test_parse_valid_json_file(self, tmp_path):
        """Test parsing valid JSON execution file."""
        execution_data = {
            "conclusion": "success",
            "messages": [
                {"role": "user", "content": "Create a PR"},
                {"role": "assistant", "content": "Created PR #123"}
            ]
        }
        
        file_path = tmp_path / "execution.json"
        file_path.write_text(json.dumps(execution_data))
        
        result = parse_execution_file(str(file_path))
        assert isinstance(result, dict)

    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file."""
        with pytest.raises(FileNotFoundError):
            parse_execution_file("/nonexistent/file.json")

    def test_parse_invalid_json(self, tmp_path):
        """Test parsing file with invalid JSON."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("{ invalid json }")
        
        with pytest.raises(json.JSONDecodeError):
            parse_execution_file(str(file_path))

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty file."""
        file_path = tmp_path / "empty.json"
        file_path.write_text("")
        
        with pytest.raises(json.JSONDecodeError):
            parse_execution_file(str(file_path))


class TestMain:
    """Test main function integration."""

    def test_main_pr_gen_mode(self, tmp_path):
        """Test main function with pr-gen mode."""
        execution_data = {
            "conclusion": "success",
            "messages": [
                {"role": "assistant", "content": "Created PR #123 at https://github.com/owner/repo/pull/123"}
            ]
        }
        
        execution_file = tmp_path / "execution.json"
        execution_file.write_text(json.dumps(execution_data))
        
        output_file = tmp_path / "output"
        output_file.write_text("")
        
        with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output_file)}):
            with patch('sys.argv', ['extract_outputs.py', '--execution-file', str(execution_file), '--mode', 'pr-gen']):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
        
        content = output_file.read_text()
        assert "pr_number=123" in content
        assert "pr_url=https://github.com/owner/repo/pull/123" in content

    def test_main_plan_gen_mode(self, tmp_path):
        """Test main function with plan-gen mode."""
        execution_data = {
            "conclusion": "success",
            "messages": [
                {"role": "assistant", "content": "# Implementation Plan\n\n1. Setup database\n2. Create API"}
            ]
        }
        
        execution_file = tmp_path / "execution.json"
        execution_file.write_text(json.dumps(execution_data))
        
        output_file = tmp_path / "output"
        output_file.write_text("")
        
        with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output_file)}):
            with patch('sys.argv', ['extract_outputs.py', '--execution-file', str(execution_file), '--mode', 'plan-gen']):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
        
        content = output_file.read_text()
        assert "plan_output<<EOF" in content
        assert "Implementation Plan" in content

    def test_main_no_outputs_found(self, tmp_path, capsys):
        """Test main function when no outputs are found."""
        execution_data = {
            "conclusion": "success",
            "messages": [
                {"role": "assistant", "content": "No PR or plan created"}
            ]
        }
        
        execution_file = tmp_path / "execution.json"
        execution_file.write_text(json.dumps(execution_data))
        
        with patch('sys.argv', ['extract_outputs.py', '--execution-file', str(execution_file), '--mode', 'pr-gen']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
        
        captured = capsys.readouterr()
        assert "No PR numbers found" in captured.out

    def test_main_file_not_found(self, capsys):
        """Test main function with nonexistent file."""
        with patch('sys.argv', ['extract_outputs.py', '--execution-file', '/nonexistent/file.json', '--mode', 'pr-gen']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
        
        captured = capsys.readouterr()
        assert "Error loading execution file" in captured.out