import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
ANSI = re.compile(r"\x1b\[[0-9;]*m|\x1b\]133;A\x1b\\")


class PromptTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.env = os.environ.copy()
        for name in ("TMUX", "PROMPT_COMMAND", "BASH_ENV"):
            self.env.pop(name, None)
        self.env.update(
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            HISTFILE=os.devnull,
            FANCY_PROMPT_USE_SYMBOLS="0",
            FANCY_PROMPT_USE_NERD_SYMBOLS="0",
        )
        self.git("init", "--quiet")
        self.git("fetch", "--quiet", str(PROJECT), "HEAD")
        self.git("checkout", "--quiet", "-b", "main", "FETCH_HEAD")

    def command(self, *args, cwd=None):
        result = subprocess.run(
            args, cwd=cwd or self.repo, env=self.env,
            text=True, capture_output=True, check=True,
        )
        self.assertEqual(result.stderr, "")
        return result.stdout

    def git(self, *args):
        return self.command("git", *args).strip()

    def prompt(self, shell="bash", cwd=None):
        return self.command(str(PROJECT / "prompt"), shell, "0", "0", "0", cwd=cwd)

    def plain(self, cwd=None):
        return ANSI.sub("", self.prompt(cwd=cwd)).replace(r"\[", "").replace(r"\]", "")

    def test_untracked_branch_containing_HEAD(self):
        self.git("branch", "-m", "fix-HEAD-display")
        output = self.plain()
        self.assertIn("fix-HEAD-display!", output)
        self.assertNotIn("->", output)

    def test_remote_tracking_branch_and_missing_ref(self):
        self.git("remote", "add", "origin", str(PROJECT))
        self.git("update-ref", "refs/remotes/origin/topic", "HEAD")
        self.git("branch", "--set-upstream-to=origin/topic", "main")
        self.assertIn("main->topic", self.plain())
        self.git("update-ref", "-d", "refs/remotes/origin/topic")
        self.assertIn("main->topic", self.plain())

    def test_local_tracking_branch_with_slash(self):
        self.git("branch", "parent/base")
        self.git("branch", "--set-upstream-to=parent/base", "main")
        self.assertIn("main->parent/base", self.plain())

    def test_detached_HEAD_and_tag(self):
        self.git("checkout", "--quiet", "--detach")
        self.assertIn(self.git("rev-parse", "--short", "HEAD") + "!", self.plain())
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "tag", "-a", "-m", "Test tag", "v1.0")
        output = self.plain()
        self.assertIn("v1.0", output)
        self.assertNotIn("v1.0!", output)

    def test_spaces_and_repository_relative_directory(self):
        renamed = self.root / "repo with spaces"
        self.repo.rename(renamed)
        self.repo = renamed
        nested = self.repo / "sub dir" / "leaf"
        nested.mkdir(parents=True)
        output = self.plain(cwd=nested)
        self.assertIn("repo with spaces/sub dir/leaf", output)
        self.assertIn("main!", output)
        self.assertNotIn("[worktree]", output)

    def test_linked_worktree_with_spaces(self):
        worktree = self.root / "linked tree"
        self.git("worktree", "add", "--quiet", "--detach", str(worktree))
        output = self.plain(cwd=worktree)
        self.assertIn("linked tree", output)
        self.assertIn("[worktree]" + self.git("rev-parse", "--short", "HEAD"), output)

    def test_inside_git_directory(self):
        self.assertIn("repo/.git/objects", self.plain(cwd=self.repo / ".git" / "objects"))

    def test_upstream_uses_cached_HEAD_without_contacting_remote(self):
        self.git("remote", "add", "upstream", str(self.root / "does-not-exist"))
        self.git("config", "remote.upstream.gh-resolved", "base")
        self.git("update-ref", "refs/remotes/upstream/main", "HEAD")
        self.git("symbolic-ref", "refs/remotes/upstream/HEAD", "refs/remotes/upstream/main")
        self.assertIn("(upstream/main)", self.plain())
        self.git("symbolic-ref", "--delete", "refs/remotes/upstream/HEAD")
        self.assertNotIn("(upstream/", self.plain())

    def test_git_query_failure_keeps_basic_prompt(self):
        self.git("config", "branch.main.upstream", "main")
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        git = bin_dir / "git"
        git.write_text(
            '#!/bin/sh\n'
            'if [ "$*" = "$FCP_TEST_FAIL" ]; then exit 128; fi\n'
            'exec "$FCP_TEST_GIT" "$@"\n'
        )
        git.chmod(0o755)
        self.env.update(
            FCP_TEST_GIT=shutil.which("git"),
            PATH=str(bin_dir) + os.pathsep + self.env["PATH"],
        )
        for query in (
            "status --untracked-files=normal --branch --porcelain --ignore-submodules",
            "submodule status --recursive",
            "branch -vv --format=%(refname:strip=2)#%(upstream:strip=3)",
            "rev-parse --path-format=absolute --abbrev-ref HEAD --git-dir --git-common-dir",
            "config --get branch.main.remote",
            "rev-list --left-right --count main...HEAD",
        ):
            with self.subTest(query=query):
                self.env["FCP_TEST_FAIL"] = query
                output = self.plain()
                self.assertIn("repo ...", output)
                self.assertNotIn("main", output)
                self.assertTrue(output.endswith("\n> "))

    def test_clean_and_dirty_tracking_branch(self):
        self.git("remote", "add", "origin", str(PROJECT))
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.git("branch", "--set-upstream-to=origin/main", "main")
        self.assertIn("main", self.plain())
        (self.repo / "added").write_text("staged\n")
        self.git("add", "added")
        (self.repo / "untracked").touch()
        output = self.plain()
        self.assertIn("main", output)
        self.assertIn("+1", output)
        self.assertIn("…1", output)

    def test_clean_submodule(self):
        self.git("-c", "protocol.file.allow=always", "submodule", "add", "--quiet",
                 str(PROJECT), "submodule")
        output = self.plain()
        self.assertIn("main!", output)
        self.assertNotIn("", output)

    def test_tmux_rename_failure_keeps_git_prompt(self):
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        tmux = bin_dir / "tmux"
        log = self.root / "tmux.log"
        tmux.write_text(
            '#!/bin/sh\n'
            'if [ "$1" = display-message ]; then echo 3; exit 0; fi\n'
            'printf "%s\\n" "$@" > "$FCP_TEST_TMUX_LOG"\n'
            'exit 1\n'
        )
        tmux.chmod(0o755)
        self.env.update(
            TMUX="test", FCP_TEST_TMUX_LOG=str(log),
            PATH=str(bin_dir) + os.pathsep + self.env["PATH"],
        )
        self.assertIn("main!", self.plain())
        self.assertEqual(log.read_text().splitlines(),
                         ["rename-window", "-t", "3", "repo#[fg=colour8][main!]"])

    def test_shell_syntax_in_names_is_displayed_literally(self):
        branch = "$(touch${IFS}executed)-`touch${IFS}executed`-%F{red}!"
        directory = r"repo $(touch executed) `touch executed` %F{red} \u ' \" ^D"
        self.git("branch", "-m", branch)
        renamed = self.root / directory
        self.repo.rename(renamed)
        self.repo = renamed

        # Use real prompt expansion, not just the helper's escaped output.
        bash_env = self.env | {"FCP_TEST_PROMPT": self.prompt()}
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-i"], cwd=self.repo, env=bash_env,
            input="PS1=$FCP_TEST_PROMPT\nexit\n", text=True, capture_output=True, check=True,
        )
        self.assertIn(branch, result.stderr)
        self.assertIn(directory, result.stderr)
        self.assertFalse((self.repo / "executed").exists())

        for option in ("nopromptsubst", "promptsubst"):
            with self.subTest(option=option):
                output = self.command(
                    "zsh", "-f", "-c",
                    'source "$1"; setopt "$2" promptbang; '
                    'fcp_set_prompt "$3"; print -Pnr -- "$PROMPT"',
                    "test", str(PROJECT / "prompt.zsh"), option, self.prompt("zsh"),
                )
                self.assertIn(branch, output)
                self.assertIn(directory, output)
                self.assertFalse((self.repo / "executed").exists())

    def test_zsh_entry_points_work_from_another_directory(self):
        plugin = self.root / "plugin with spaces"
        plugin.mkdir()
        for name in ("prompt", "prompt.zsh", "fancy-prompt.plugin.zsh"):
            shutil.copy2(PROJECT / name, plugin / name)
        for entry in ("prompt.zsh", "fancy-prompt.plugin.zsh"):
            with self.subTest(entry=entry):
                output = self.command(
                    "zsh", "-f", "-c",
                    'source "$1"; '
                    '(( ${precmd_functions[(Ie)fcp_prompt_precmd]} && '
                    '${preexec_functions[(Ie)fcp_cmd_timer_preexec]} )) || exit 1; '
                    'fcp_set_prompt "$(fcp_update_prompt_sub 0 0)"; '
                    'print -Pnr -- "$PROMPT"',
                    "test", str(plugin / entry),
                )
                self.assertIn("main!", output)


if __name__ == "__main__":
    unittest.main()
