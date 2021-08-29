from pathlib import Path
from typing import List

import yaml


def list_files(root: Path, exts: List[str]) -> List[Path]:
    def valid(p: Path):
        return not any([part.startswith(".") for part in p.relative_to(root).parts])

    paths = (
        [p for ext in exts for p in Path(root).rglob(f"*.{ext}") if valid(p)]
        if len(exts)
        else [p for p in Path(root).rglob(f"*") if valid(p)]
    )

    return sorted(paths)


def prepare_style(root: Path, base, overwrite):
    path = root / ".clang-format"
    style = {**base, **overwrite}
    with open(path, "w") as f:
        yaml.safe_dump(style, f, sort_keys=False)


if __name__ == "__main__":
    import json
    from itertools import product
    from shutil import rmtree
    from sys import stdout

    from exec_tool import (
        clang_format,
        clang_format_dump,
        clang_format_version,
        git_clone,
        git_diff_stat,
    )

    # load specifications
    format_style_options = Path(
        f"specification/ClangFormatStyleOptions-{clang_format_version()}.json"
    ).read_text()
    format_style_options = json.loads(format_style_options)

    predifined = format_style_options[0]["values"]
    options = format_style_options[1:]

    # clone repo
    repo = "https://github.com/intel/SGXDataCenterAttestationPrimitives.git"
    path = git_clone(repo)

    # find all cpp files
    files = list_files(path, ["cpp", "h"])

    # find a style to base on
    stat = {}
    for base, indent in product(predifined, [2, 4]):
        clang_format(path, {"BasedOnStyle": base, "IndentWidth": indent}, files)
        f, i, d = git_diff_stat(path)
        stat[(base, indent)] = (f, i, d)

    (base, indent), (min_f, min_ins, min_del) = min(
        stat.items(), key=lambda t: t[1][1] + t[1][2]
    )

    print("! The BasedOnStyle chosen is", base, "with indent width", indent)
    print("! The corresponding minimum change is", min_f, min_ins, min_del)

    style = {"BasedOnStyle": base, "Language": "Cpp", "IndentWidth": indent}

    base_style = clang_format_dump(style)

    def try_overwrite(overwrite):
        global min_ins, min_del

        prepare_style(path, style, overwrite)
        clang_format(path, "file", files)
        f, i, d = git_diff_stat(path)

        if i + d < min_ins + min_del:
            style.update(overwrite)
            min_f, min_ins, min_del = f, i, d

    for _ in range(3):
        for option in options:
            if option.get("key") in style:
                continue

            key = option.get("key")
            print("+ Trying key ", key)

            if option.get("type") == "NEST":
                subbase = base_style.get(key)
                for opt in option.get("values"):
                    substyle = style.get(key, {})
                    if opt["key"] in substyle:
                        continue

                    for v in opt["values"]:
                        if str(v).lower() == str(subbase.get(opt["key"])).lower():
                            continue

                        try_overwrite({key: {**substyle, **{opt["key"]: v}}})
            else:
                for val in option.get("values"):
                    if str(val).lower() == str(base_style[key]).lower():
                        continue

                    try_overwrite({key: val})

    print(style)
    print("---")
    yaml.dump(style, stdout, sort_keys=False)
    print("---")

    print("Removing", path)
    rmtree(path)
