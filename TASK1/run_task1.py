#!/usr/bin/env python3
"""一键完成 TASK1：AkShare 拉取数据 + 生成 PDF 报告。"""

import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent


def main() -> None:
    name = os.environ.get("STUDENT_NAME", "姓名")
    print(f"提交文件名: {name}TASK1.pdf\n")

    print(">>> 步骤1: AkShare 获取数据并绘图")
    subprocess.run([sys.executable, str(BASE / "akshare_fetch.py")], check=True)

    print(">>> 步骤2: 生成 Word 报告")
    env = os.environ.copy()
    env["STUDENT_NAME"] = name
    subprocess.run([sys.executable, str(BASE / "generate_docx.py")], check=True, env=env)

    print(">>> 步骤3: 生成 PDF 报告（可选）")
    subprocess.run([sys.executable, str(BASE / "generate_pdf.py")], check=True, env=env)

    print(f"\n完成！请检查并提交:")
    print(f"  Word: {BASE / f'{name}TASK1.docx'}")
    print(f"  PDF : {BASE / f'{name}TASK1.pdf'}")


if __name__ == "__main__":
    main()
