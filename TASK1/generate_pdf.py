#!/usr/bin/env python3
"""生成 TASK1 提交用 PDF（宋体、五号、1.5 倍行距、两端对齐）。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

BASE_DIR = Path(__file__).resolve().parent
FIG1 = BASE_DIR / "figures" / "fig1_close_price.png"
FIG2 = BASE_DIR / "figures" / "fig2_kline_volume.png"
CSV_PATH = BASE_DIR / "data" / "smic_688981_daily.csv"

FONT_PATH = "/System/Library/Fonts/Supplemental/Songti.ttc"
STUDENT_NAME = os.environ.get("STUDENT_NAME", "姓名")
OUTPUT_PDF = BASE_DIR / f"{STUDENT_NAME}TASK1.pdf"

FONT_SIZE = 10.5
LINE_SPACING = FONT_SIZE * 1.5


def register_font() -> str:
    pdfmetrics.registerFont(TTFont("Songti", FONT_PATH, subfontIndex=0))
    return "Songti"


def body_style(font_name: str) -> ParagraphStyle:
    return ParagraphStyle(
        name="Body",
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=LINE_SPACING,
        alignment=TA_JUSTIFY,
        spaceBefore=0,
        spaceAfter=0,
        firstLineIndent=21,
    )


def heading_style(font_name: str, level: int = 1) -> ParagraphStyle:
    sizes = {1: 14, 2: 12, 3: 11}
    return ParagraphStyle(
        name=f"H{level}",
        fontName=font_name,
        fontSize=sizes.get(level, 11),
        leading=sizes.get(level, 11) * 1.5,
        alignment=TA_JUSTIFY,
        spaceBefore=6,
        spaceAfter=6,
        firstLineIndent=0,
    )


def title_style(font_name: str) -> ParagraphStyle:
    return ParagraphStyle(
        name="Title",
        fontName=font_name,
        fontSize=16,
        leading=24,
        alignment=TA_CENTER,
        spaceBefore=12,
        spaceAfter=18,
    )


def ensure_data() -> None:
    if not CSV_PATH.exists() or not FIG1.exists():
        subprocess.run([sys.executable, str(BASE_DIR / "akshare_fetch.py")], check=True)


def add_figure(story: list, path: Path, caption: str, h2, width=15 * cm, height=7.5 * cm) -> None:
    if path.exists():
        story.append(Spacer(1, 0.3 * cm))
        story.append(Image(str(path), width=width, height=height))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(caption, h2))


def build_story(font_name: str) -> list:
    body = body_style(font_name)
    h1 = heading_style(font_name, 1)
    h2 = heading_style(font_name, 2)
    title = title_style(font_name)
    story: list = []

    story.append(Paragraph("量化交易基础与 AkShare 数据实践", title))
    story.append(Paragraph("TASK1 作业报告", title))
    story.append(Spacer(1, 0.5 * cm))

    # ===== 问题 1 =====
    story.append(Paragraph("一、量化交易相较于传统手工交易的优势", h1))
    for p in [
        "随着金融市场数据化、自动化程度不断提高，量化交易（Quantitative Trading）已成为机构与个人投资者的重要参与方式。相较于依赖人工盯盘、凭经验下单的传统手工交易，量化交易在效率、纪律性与可验证性方面具有显著优势。",
        "第一，量化交易能够克服人性弱点。手工交易容易受到贪婪、恐惧、过度自信等情绪影响，导致追涨杀跌、频繁交易等非理性行为。量化策略依据预先设定的规则自动执行，减少主观情绪对决策的干扰。",
        "第二，量化交易具有更高的执行效率。计算机可在毫秒级完成行情扫描、信号识别与下单，能同时监控大量标的，捕捉短暂出现的交易机会。",
        "第三，量化交易支持历史回测与策略验证。策略可在多年历史数据上模拟运行，评估收益率、最大回撤等指标，在实盘前检验有效性。",
        "第四，量化交易强调一致性与可复制性。同一套规则可重复应用，便于团队协作与策略迭代。",
        "第五，量化交易便于风险管控。可通过程序设定止损、止盈、仓位上限等规则，实时监控风险敞口。",
        "第六，量化交易能够处理海量信息。量化模型可综合价格、成交量、财务等多维数据进行分析，而人工分析的信息容量有限。",
        "综上所述，量化交易将投资逻辑代码化、流程化、数据化，为策略研究提供了可量化、可复现的框架。本次作业通过 Python + AkShare 获取行情、绘图、存档，正是量化研究流程的具体实践。",
    ]:
        story.append(Paragraph(p, body))
        story.append(Spacer(1, 0.15 * cm))

    story.append(PageBreak())

    # ===== 问题 2 =====
    story.append(Paragraph("二、基本概念解释：K 线、基本面、技术面", h1))

    story.append(Paragraph("（一）K 线", h2))
    for p in [
        "K 线（Candlestick Chart）是展示证券价格在某一时间段内开盘价、收盘价、最高价、最低价及其涨跌关系的图形工具。每根 K 线由实体与上下影线组成：实体上端为收盘价、下端为开盘价（A 股习惯红色上涨、绿色下跌）；影线表示最高价与最低价。",
        "K 线可按日 K、周 K、月 K 等周期划分。通过连续 K 线组合，可观察趋势、支撑/压力位及常见形态，是技术分析中最基础的可视化方式。本作业图2 即采用日 K 线展示中芯国际价格与成交量。",
    ]:
        story.append(Paragraph(p, body))
        story.append(Spacer(1, 0.15 * cm))

    story.append(Paragraph("（二）基本面", h2))
    for p in [
        "基本面（Fundamental Analysis）从宏观经济、行业状况与公司内在价值出发，评估证券合理价格。其核心逻辑是价格长期围绕内在价值波动，通过研究盈利能力与成长性，判断资产是否被高估或低估。",
        "股票基本面包括：宏观层面（GDP、利率、政策等）；行业层面（竞争格局、景气周期）；公司层面（营收、净利润、现金流、市盈率等）。基本面分析适合中长期投资，回答“买什么、值不值得买”。",
    ]:
        story.append(Paragraph(p, body))
        story.append(Spacer(1, 0.15 * cm))

    story.append(Paragraph("（三）技术面", h2))
    for p in [
        "技术面（Technical Analysis）基于历史价格、成交量等市场行为数据，运用图表与指标预测价格走势。其假设包括：市场行为包容一切信息、价格沿趋势运动、历史会重演。",
        "常见工具有 K 线形态、移动平均线（MA）、MACD、RSI 等。技术面侧重“何时买卖”，与基本面形成互补。本作业通过收盘价曲线（图1）与日 K 线（图2）进行技术面观察。",
    ]:
        story.append(Paragraph(p, body))
        story.append(Spacer(1, 0.15 * cm))

    story.append(PageBreak())

    # ===== 问题 3 =====
    story.append(Paragraph("三、AkShare 数据获取与 Python 实现", h1))

    story.append(Paragraph("（一）AkShare 平台与数据接口", h2))
    for p in [
        "AkShare（https://akshare.akfamily.xyz/）是开源 Python 财经数据接口库，pip install akshare 即可使用，无需注册 Token，适合量化入门与教学实验。",
        "本作业以半导体龙头中芯国际 A 股（688981）为例，调用 ak.stock_zh_a_daily 接口获取上交所科创板股票近一年每个交易日的日线数据（前复权），字段包括 date、open、high、low、close、volume、amount 等。",
        "在完成作业基本要求之外，我们还使用 ak.stock_hk_daily 获取港股 00981 数据，用 ak.currency_boc_sina 获取港元/人民币汇率，完成了 A/H 股对比分析与 GitHub Pages 交互看板（dashboard.html），详见 smic_analysis.ipynb。",
    ]:
        story.append(Paragraph(p, body))
        story.append(Spacer(1, 0.15 * cm))

    story.append(Paragraph("（二）Python 实现步骤", h2))
    for p in [
        "实现流程如下：① 安装 akshare、pandas、matplotlib；② 设定股票代码 sh688981 与起止日期（近 365 个自然日）；③ 调用 stock_zh_a_daily 拉取日线并按 date 排序；④ 用 matplotlib 绘制每日收盘价曲线（图1）；⑤ 用 mplfinance 绘制日 K 线与成交量（图2）；⑥ 将数据保存为 UTF-8 编码 CSV，供后续任务使用。完整代码见 TASK1/akshare_fetch.py。",
        "核心代码片段：df = ak.stock_zh_a_daily(symbol='sh688981', start_date='...', end_date='...', adjust='qfq')。adjust='qfq' 表示前复权，消除除权除息对价格连续性的影响，便于趋势分析。",
    ]:
        story.append(Paragraph(p, body))
        story.append(Spacer(1, 0.15 * cm))

    add_figure(story, FIG1, "图1  中芯国际（688981）近一年每日收盘价", h2)

    rows = 0
    date_range = "—"
    ret_text = "—"
    if CSV_PATH.exists():
        import pandas as pd

        df = pd.read_csv(CSV_PATH)
        rows = len(df)
        date_range = f"{df['date'].iloc[0]} ~ {df['date'].iloc[-1]}"
        ret = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
        ret_text = f"{ret:+.2f}%"

    for p in [
        f"图1 展示了中芯国际（688981）在过去约 {rows} 个交易日内的前复权收盘价走势（{date_range}）。解读如下：① 区间整体涨跌幅约为 {ret_text}，反映市场对公司价值的重估过程；② 2025 年下半年至 2026 年上半年价格中枢明显抬升，显示资金关注度提高；③ 近期出现回调，需结合成交量（图2）判断是技术性调整还是趋势反转。",
        "收盘价曲线是最常用的技术面观察工具，可快速识别趋势方向与关键价位。相比手工在 Excel 中逐日录入，Python + AkShare 可一键获取完整历史数据并自动出图，体现了量化研究在效率上的优势。",
    ]:
        story.append(Paragraph(p, body))
        story.append(Spacer(1, 0.15 * cm))

    add_figure(story, FIG2, "图2  中芯国际（688981）日K线及成交量", h2, height=8.5 * cm)

    for p in [
        "图2 以日 K 线形式展示开高低收，下方柱状图为成交量。解读如下：① 红色 K 线表示当日收盘价高于开盘价（上涨），绿色表示下跌，符合 A 股配色习惯；② 价涨量增通常表示上涨动能较强，价跌量缩可能表示抛压减轻；③ 图中可见若干放量长阳，往往对应重要信息释放或资金集中流入的时段。",
        "该图与项目 dashboard.html 看板、smic_analysis.ipynb Notebook 中的 K 线分析一致，是从数据获取到可视化展示的完整技术面实践。",
    ]:
        story.append(Paragraph(p, body))
        story.append(Spacer(1, 0.15 * cm))

    story.append(Paragraph("（三）CSV 数据保存", h2))
    for p in [
        f"数据已保存至 TASK1/data/smic_688981_daily.csv，共 {rows} 行，字段包括 date、open、high、low、close、volume、amount、outstanding_share、turnover 等，可直接用 pandas.read_csv 读取。",
        "CSV 采用 utf-8-sig 编码，兼容 Excel 中文显示。项目根目录 data/ 下还保存了 A/H 股对比数据（smic_688981_a.csv、smic_00981_hk.csv），可用于后续因子计算、回测或 AH 溢价分析。",
    ]:
        story.append(Paragraph(p, body))
        story.append(Spacer(1, 0.15 * cm))

    return story


def main() -> None:
    ensure_data()
    font_name = register_font()
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )
    doc.build(build_story(font_name))
    print(f"PDF 已生成: {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
