import re
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Any, List, Tuple, Union
from uuid import uuid4

import yaml

TMP = Path("/tmp")
CLANG_FORMAT = "clang-format"


def git_clone(repo_url: str) -> Path:
    destination = TMP / uuid4().hex
    with Popen(["git", "clone", repo_url, destination]) as proc:
        print("+ Repository cloned to ", destination)

    return destination


def git_diff_stat(root: Path) -> Tuple[int, int, int]:
    REGEXP = re.compile(
        "(?P<f>\d+) files changed, (?P<ins>\d+) insertions\(\+\), (?P<del>\d+) deletions\(-\)"
    )

    with Popen(
        ["git", "--no-pager", "diff", "--shortstat"], stdout=PIPE, cwd=root
    ) as proc:
        line = proc.stdout.read().decode().strip()
        if line == "":
            return 0, 0, 0

        print("+", line)
        mobj = REGEXP.search(line).groupdict()
        return int(mobj.get("f")), int(mobj.get("ins")), int(mobj.get("del"))


def git_reset(root: Path):
    with Popen(["git", "reset", "--hard"], cwd=root, stdout=PIPE) as proc:
        print("+ Repository reset")


def clang_format(root: Path, style, files: List[Union[str, Path]]):
    git_reset(root)

    if type(style) == dict:
        style = "{" + ", ".join([f"{k}: {v}" for k, v in style.items()]) + "}"

    if style == "file":
        with open(root / ".clang-format", "r") as f:
            print("+ Formating with style", yaml.safe_load(f))
    else:
        print("+ Formating with style", style)

    files = [str(f) for f in files]

    with Popen([CLANG_FORMAT, f"--style={style}", "-i"] + files, cwd=root) as p:
        pass


def clang_format_version() -> int:
    REGEXP = re.compile("clang-format version (?P<version>\d+)\.")

    with Popen([CLANG_FORMAT, "--version"], stdout=PIPE) as proc:
        version_string = proc.stdout.read().decode()

    mobj = REGEXP.search(version_string)
    if mobj is None:
        raise RuntimeError("Unrecognizable version string", version_string)
    else:
        return int(mobj.groupdict().get("version"))


def clang_format_dump(style) -> Any:
    if type(style) == dict:
        style = (
            "{"
            + ", ".join(
                [
                    f"{k}: { str(v).lower() if type(v)==bool else v}"
                    for k, v in style.items()
                ]
            )
            + "}"
        )

    with Popen([CLANG_FORMAT, f"--style={style}", "--dump-config"], stdout=PIPE) as p:
        return yaml.safe_load(p.stdout)
