#!/usr/bin/env python3
"""替换 Word 文档中的图1、图2（保留用户其余修改）。"""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
FIG1 = BASE / "figures" / "fig1_close_price.png"
FIG2 = BASE / "figures" / "fig2_kline_volume.png"


def replace_images(docx_path: Path, out_path: Path | None = None) -> Path:
    if out_path is None:
        out_path = docx_path

    tmp = docx_path.with_suffix(".tmp.docx")
    shutil.copy2(docx_path, tmp)

    replacements = {
        "word/media/image1.png": FIG1,
        "word/media/image2.png": FIG2,
    }

    with zipfile.ZipFile(tmp, "r") as zin, zipfile.ZipFile(out_path, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in replacements and replacements[item.filename].exists():
                data = replacements[item.filename].read_bytes()
            zout.writestr(item, data)

    tmp.unlink(missing_ok=True)
    return out_path


def main() -> None:
    targets = [
        BASE / "张利伟 TASK1.docx",
        BASE / "张利伟 TASK1_updated.docx",
        BASE / "张利伟TASK1.docx",
    ]
    if len(sys.argv) > 1:
        targets = [Path(sys.argv[1])]

    for doc in targets:
        if not doc.exists():
            continue
        replace_images(doc)
        print(f"已更新图片: {doc}")


if __name__ == "__main__":
    main()
