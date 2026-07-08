#!/usr/bin/env python3
"""TASK2 一键：分析 + 生成 PDF。"""

import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent


def main():
    name = os.environ.get("STUDENT_NAME", "姓名")
    print(f"提交文件: {name}TASK2.pdf\n")

    print(">>> 步骤1: 数据诊断与指标计算")
    subprocess.run([sys.executable, str(BASE / "task2_analysis.py")], check=True)

    print(">>> 步骤2: 生成 Word 报告")
    env = os.environ.copy()
    env["STUDENT_NAME"] = name
    subprocess.run([sys.executable, str(BASE / "generate_docx.py")], check=True, env=env)

    print(">>> 步骤3: 生成 PDF 报告")
    subprocess.run([sys.executable, str(BASE / "generate_pdf.py")], check=True, env=env)

    print(f"\n完成:")
    print(f"  Word: {BASE / f'{name}TASK2.docx'}")
    print(f"  PDF : {BASE / f'{name}TASK2.pdf'}")


if __name__ == "__main__":
    main()
