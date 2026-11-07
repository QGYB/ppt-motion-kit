# SPDX-License-Identifier: AGPL-3.0-only
"""Check declared font families in a PowerPoint package against the skill's palette."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile


A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
STRICT_A = "{http://purl.oclc.org/ooxml/drawingml/main}"
EMBEDDABLE = {"Noto Sans SC", "Noto Serif SC"}
APPROVED = EMBEDDABLE | {"庞门正道粗书体", "庞门正道粗书体6.0", "PangMenZhengDao-Cu6.0"}
APPROVED_NAMES = {name.casefold() for name in APPROVED}
EMBEDDABLE_NAMES = {name.casefold() for name in EMBEDDABLE}
THEME_FACES = {f"+{role}-{script}" for role in ("mj", "mn") for script in ("lt", "ea", "cs")}


def check_theme(root, ns):
    issues = []
    for role in ("majorFont", "minorFont"):
        family = root.find(f".//{ns}fontScheme/{ns}{role}")
        if family is None:
            issues.append(f"{role} 缺少字体方案")
            continue
        latin = family.find(ns + "latin")
        east = family.find(ns + "ea")
        hans = family.find(f"{ns}font[@script='Hans']")
        if latin is None or not latin.get("typeface", "").strip():
            issues.append(f"{role} 缺少西文字体")
        if not any(n is not None and n.get("typeface", "").strip() for n in (east, hans)):
            issues.append(f"{role} 缺少东亚或简体中文字体")
        if any(n.get("typeface", "").strip() in THEME_FACES for n in family):
            issues.append(f"{role} 主题字体需要填写具体家族")
    return issues


def audit(package):
    members = package.namelist()
    if "ppt/presentation.xml" not in members:
        raise ValueError("文件中没有 PowerPoint 主文稿")
    declared = defaultdict(set)
    theme_issues = []
    embedding_issues = set()
    themes = 0
    manual = set()
    for name in members:
        if not name.startswith("ppt/"):
            continue
        if name.startswith(("ppt/media/", "ppt/embeddings/")):
            if not name.endswith("/"):
                manual.add(name.rsplit("/", 1)[0])
            continue
        if not name.endswith(".xml"):
            continue
        root = ET.fromstring(package.read(name))
        for embedded in root.findall(".//{*}embeddedFont/{*}font"):
            face = embedded.get("typeface", "").strip()
            if face.casefold() not in EMBEDDABLE_NAMES:
                embedding_issues.add(face or "未命名字体")
        if root.tag in (A + "theme", STRICT_A + "theme"):
            themes += 1
            ns = root.tag[:root.tag.index("}") + 1]
            theme_issues.extend(f"{name}: {issue}" for issue in check_theme(root, ns))
        for node in root.iter():
            face = node.get("typeface", "").strip()
            if face and face not in THEME_FACES:
                declared[face].add(name)
    if not themes:
        theme_issues.append("缺少可核对的文稿主题")
    outside = {face: sorted(parts) for face, parts in sorted(declared.items())
               if face.casefold() not in APPROVED_NAMES}
    return {
        "显式字体检查通过": bool(declared) and not outside and not theme_issues and not embedding_issues,
        "全部显式字体": sorted(declared),
        "清单外字体与部件": outside,
        "主题问题": theme_issues,
        "清单未批准嵌入的字体": sorted(embedding_issues),
        "需人工复核": [
            "检查转曲字字源、各语种缺字与目标软件回退",
            *[f"{part} 中的媒体或内嵌对象若含文字，复核其来源与字体" for part in sorted(manual)],
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("presentation", type=Path)
    path = parser.parse_args().presentation
    try:
        with ZipFile(path) as package:
            report = audit(package)
    except (BadZipFile, OSError, ValueError, ET.ParseError) as exc:
        parser.exit(2, f"不能核对 {path}: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["显式字体检查通过"] else 1


if __name__ == "__main__":
    sys.exit(main())
