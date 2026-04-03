"""回归测试：clone 后 .worktrees/ 写入 .git/info/exclude，而非 .gitignore，不产生 unstaged changes。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from monarbor.cli import _ensure_in_git_exclude


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """创建一个本地 git 仓库（含初始提交）。"""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def test_ensure_in_git_exclude_writes_to_exclude(git_repo: Path):
    """.worktrees/ 应写入 .git/info/exclude，而不是 .gitignore。"""
    _ensure_in_git_exclude(git_repo, ".worktrees/")

    exclude_path = git_repo / ".git" / "info" / "exclude"
    assert exclude_path.exists(), ".git/info/exclude 应存在"
    assert ".worktrees/" in exclude_path.read_text(encoding="utf-8")


def test_ensure_in_git_exclude_does_not_modify_gitignore(git_repo: Path):
    """调用后 .gitignore 不应被创建或修改。"""
    gitignore_path = git_repo / ".gitignore"
    assert not gitignore_path.exists(), "前提：.gitignore 不存在"

    _ensure_in_git_exclude(git_repo, ".worktrees/")

    assert not gitignore_path.exists(), ".gitignore 不应被创建"


def test_ensure_in_git_exclude_does_not_dirty_working_tree(git_repo: Path):
    """写入 .git/info/exclude 后，工作区应保持干净（无 unstaged changes）。"""
    _ensure_in_git_exclude(git_repo, ".worktrees/")

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=git_repo,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "", f"工作区应干净，实际输出: {result.stdout!r}"


def test_ensure_in_git_exclude_idempotent(git_repo: Path):
    """重复调用不应重复写入条目。"""
    _ensure_in_git_exclude(git_repo, ".worktrees/")
    _ensure_in_git_exclude(git_repo, ".worktrees/")

    exclude_path = git_repo / ".git" / "info" / "exclude"
    content = exclude_path.read_text(encoding="utf-8")
    assert content.count(".worktrees/") == 1, "条目不应重复"
