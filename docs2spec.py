# !/usr/bin/env python3

import re
from dataclasses import dataclass
from typing import Any, List


@dataclass
class Option:
    key: str
    value_type: str
    possible_values: List[Any]


class Parser:
    text: str

    predefined_styles: List[str] = []
    options: List[Option] = []

    existing: bool = False
    current_option: Option

    REGEXP_HEADER = re.compile("\*\*(?P<key>\w+)\*\* \(``(?P<type>\w+)``\)")
    REGEXP_OPTION = re.compile("\(in configuration: ``(?P<option>\w+)``\)")

    def __init__(self, doc: str):
        BASE = "**BasedOnStyle** (``string``)"
        START = ".. START_FORMAT_STYLE_OPTIONS"
        END = ".. END_FORMAT_STYLE_OPTIONS"

        pos = {
            "base": doc.find(BASE),
            "start": doc.find(START),
            "end": doc.find(END),
        }

        # find predefined styles
        based_on_style = doc[pos["base"] + len(BASE) : pos["start"]]
        REGEXP_STYLE = re.compile("\* ``(?P<style>\w+)``", re.MULTILINE)
        mobj = REGEXP_STYLE.search(based_on_style)
        while mobj:
            self.predefined_styles.append(mobj.groupdict().get("style"))
            mobj = REGEXP_STYLE.search(based_on_style, pos=mobj.span()[1])

        # find format style options
        self.text = doc[pos["start"] + len(START) : pos["end"]].strip()

    def parse(self) -> List[Option]:
        for line in self.text.splitlines():
            if self.parse_header(line):
                continue
            if self.parse_option_type(line):
                continue
            if self.parse_option(line):
                continue

        self.options.append(self.current_option)
        self.existing = False
        return self.options

    def parse_header(self, line: str) -> bool:
        mobj = self.REGEXP_HEADER.search(line)
        if mobj:
            if self.existing:
                self.options.append(self.current_option)
            else:
                self.existing = True

            key = mobj.groupdict().get("key")
            value_type = mobj.groupdict().get("type")
            possible_values = []
            if value_type == "bool":
                possible_values = [True, False]

            self.current_option = Option(key, value_type, possible_values)
            return True
        else:
            return False

    def parse_option_type(self, line: str) -> bool:
        if self.current_option.value_type == "NEST":
            return False

        if "Possible values:" == line.strip():
            self.current_option.value_type = "ENUM"
            return True

        if "Nested configuration flags:" == line.strip():
            self.current_option.value_type = "NEST"
            return True

        return False

    def parse_option(self, line: str) -> bool:
        mobj = self.REGEXP_OPTION.search(line)
        if mobj:
            option = mobj.groupdict().get("option")
            self.current_option.possible_values.append(option)
            return True
        else:
            return False


if __name__ == "__main__":
    from pathlib import Path
    from exec_tool import clang_format_version
    import json

    # load specifications
    format_style_options = Path(
        f"specification/ClangFormatStyleOptions-{clang_format_version()}.rst"
    ).read_text()

    parser = Parser(format_style_options)

    predifined = parser.predefined_styles
    options = parser.parse()

    output = []
    for opt in options:
        output.append(
            {"key": opt.key, "type": opt.value_type, "values": opt.possible_values}
        )

    print(json.dumps(output, indent=True))
