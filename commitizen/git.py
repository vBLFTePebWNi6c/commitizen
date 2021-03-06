import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional

from commitizen import cmd


class GitObject:
    def __eq__(self, other):
        if not isinstance(other, GitObject):
            return False
        return self.rev == other.rev


class GitCommit(GitObject):
    def __init__(self, rev, title, body=""):
        self.rev = rev.strip()
        self.title = title.strip()
        self.body = body.strip()

    @property
    def message(self):
        return f"{self.title}\n\n{self.body}"

    def __repr__(self):
        return f"{self.title} ({self.rev})"


class GitTag(GitObject):
    def __init__(self, name, rev, date):
        self.rev = rev.strip()
        self.name = name.strip()
        self.date = date.strip()

    def __repr__(self):
        return f"{self.name} ({self.rev})"


def tag(tag: str):
    c = cmd.run(f"git tag {tag}")
    return c


def commit(message: str, args=""):
    f = NamedTemporaryFile("wb", delete=False)
    f.write(message.encode("utf-8"))
    f.close()
    c = cmd.run(f"git commit {args} -F {f.name}")
    os.unlink(f.name)
    return c


def get_commits(
    start: Optional[str] = None,
    end: str = "HEAD",
    *,
    log_format: str = "%H%n%s%n%b",
    delimiter: str = "----------commit-delimiter----------",
) -> List[GitCommit]:
    """
    Get the commits betweeen start and end
    """
    git_log_cmd = f"git log --pretty={log_format}{delimiter}"

    if start:
        c = cmd.run(f"{git_log_cmd} {start}..{end}")
    else:
        c = cmd.run(f"{git_log_cmd} {end}")

    if not c.out:
        return []

    git_commits = []
    for rev_and_commit in c.out.split(delimiter):
        rev_and_commit = rev_and_commit.strip()
        if not rev_and_commit:
            continue
        rev, title, *body_list = rev_and_commit.split("\n")

        if rev_and_commit:
            git_commit = GitCommit(
                rev=rev.strip(), title=title.strip(), body="\n".join(body_list).strip()
            )
            git_commits.append(git_commit)
    return git_commits


def get_tags(dateformat: str = "%Y-%m-%d") -> List[GitTag]:
    inner_delimiter = "---inner_delimiter---"
    formatter = (
        f"'%(refname:lstrip=2){inner_delimiter}"
        f"%(objectname){inner_delimiter}"
        f"%(committerdate:format:{dateformat})'"
    )
    c = cmd.run(f"git tag --format={formatter} --sort=-committerdate")
    if c.err or not c.out:
        return []

    git_tags = [GitTag(*line.split(inner_delimiter)) for line in c.out.split("\n")[:-1]]
    return git_tags


def tag_exist(tag: str) -> bool:
    c = cmd.run(f"git tag --list {tag}")
    return tag in c.out


def get_latest_tag_name() -> Optional[str]:
    c = cmd.run("git describe --abbrev=0 --tags")
    if c.err:
        return None
    return c.out.strip()


def get_tag_names() -> Optional[List[str]]:
    c = cmd.run("git tag --list")
    if c.err:
        return []
    return [tag.strip() for tag in c.out.split("\n") if tag.strip()]


def find_git_project_root() -> Optional[Path]:
    c = cmd.run("git rev-parse --show-toplevel")
    if not c.err:
        return Path(c.out.strip())
    return None


def is_staging_clean() -> bool:
    """Check if staing is clean"""
    c = cmd.run("git diff --no-ext-diff --name-only")
    c_cached = cmd.run("git diff --no-ext-diff --cached --name-only")
    return not (bool(c.out) or bool(c_cached.out))
