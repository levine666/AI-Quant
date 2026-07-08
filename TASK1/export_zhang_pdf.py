#!/usr/bin/env python3
"""将 Word 中的图片替换为最新 fig1/fig2，并导出 PDF。"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
FIG1 = BASE / "figures" / "fig1_close_price.png"
FIG2 = BASE / "figures" / "fig2_kline_volume.png"


def refresh_figures() -> None:
    subprocess.run([sys.executable, str(BASE / "akshare_fetch.py")], check=True)


def replace_images_in_docx(docx_path: Path, out_path: Path) -> None:
    """按文件名顺序替换 word/media 下的 PNG/JPEG 图片。"""
    new_images = [FIG1, FIG2]
    tmp = out_path.with_suffix(".tmp.docx")
    shutil.copy2(docx_path, tmp)

    with zipfile.ZipFile(tmp, "r") as zin:
        media_files = sorted(
            n for n in zin.namelist() if n.startswith("word/media/") and n.lower().endswith((".png", ".jpeg", ".jpg"))
        )
        if not media_files:
            raise RuntimeError("Word 文档中未找到图片，请确认已插入图1、图2。")

        replacements = {}
        for i, media_name in enumerate(media_files):
            if i < len(new_images) and new_images[i].exists():
                replacements[media_name] = new_images[i].read_bytes()

        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename in replacements:
                    data = replacements[item.filename]
                zout.writestr(item, data)

    tmp.unlink(missing_ok=True)


def docx_to_pdf(docx_path: Path, pdf_path: Path) -> None:
    from docx2pdf import convert

    convert(str(docx_path), str(pdf_path))


def main() -> None:
    src = BASE / "张利伟 TASK1.docx"
    if not src.exists():
        raise FileNotFoundError(f"未找到: {src}")

    print(">>> 重新生成图表（修复 Mac 中文字体）")
    refresh_figures()

    updated_docx = BASE / "张利伟 TASK1_updated.docx"
    print(">>> 更新 Word 中的图片")
    replace_images_in_docx(src, updated_docx)

    pdf_path = BASE / "张利伟TASK1.pdf"
    print(">>> 导出 PDF")
    docx_to_pdf(updated_docx, pdf_path)

    # 覆盖回原文件名，方便用户继续使用
    shutil.copy2(updated_docx, src)
    print(f"\n完成:")
    print(f"  Word: {src}")
    print(f"  PDF : {pdf_path}")


if __name__ == "__main__":
    main()
