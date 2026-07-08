#!/usr/bin/env python3
"""生成 TASK2 提交用 PDF（宋体、五号、1.5 倍行距、两端对齐）。"""

from __future__ import annotations

import json
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

BASE = Path(__file__).resolve().parent
FIG = BASE / "figures"
REPORT = BASE / "report"
FONT_PATH = "/System/Library/Fonts/Supplemental/Songti.ttc"
STUDENT_NAME = os.environ.get("STUDENT_NAME", "姓名")
OUTPUT = BASE / f"{STUDENT_NAME}TASK2.pdf"

FONT_SIZE = 10.5
LINE_SPACING = FONT_SIZE * 1.5


def register_font() -> str:
    pdfmetrics.registerFont(TTFont("Songti", FONT_PATH, subfontIndex=0))
    return "Songti"


def body(font_name: str) -> ParagraphStyle:
    return ParagraphStyle(
        name="Body", fontName=font_name, fontSize=FONT_SIZE,
        leading=LINE_SPACING, alignment=TA_JUSTIFY,
        spaceBefore=0, spaceAfter=0, firstLineIndent=21,
    )


def heading(font_name: str, level: int = 1) -> ParagraphStyle:
    sizes = {1: 14, 2: 12, 3: 11}
    return ParagraphStyle(
        name=f"H{level}", fontName=font_name, fontSize=sizes.get(level, 11),
        leading=sizes.get(level, 11) * 1.5, alignment=TA_JUSTIFY,
        spaceBefore=6, spaceAfter=6, firstLineIndent=0,
    )


def title(font_name: str) -> ParagraphStyle:
    return ParagraphStyle(
        name="Title", fontName=font_name, fontSize=16, leading=24,
        alignment=TA_CENTER, spaceBefore=12, spaceAfter=18,
    )


def add_img(story, path: Path, caption: str, h2, w=15 * cm, h=7 * cm):
    if path.exists():
        story += [Spacer(1, 0.2 * cm), Image(str(path), width=w, height=h), Spacer(1, 0.15 * cm)]
        story.append(Paragraph(caption, h2))


def load_json(name: str) -> dict:
    p = REPORT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def ensure_figures():
    if not (FIG / "fig1_diagnostic.png").exists():
        subprocess.run([sys.executable, str(BASE / "task2_analysis.py")], check=True)


def build_story(font_name: str) -> list:
    b = body(font_name)
    h1 = heading(font_name, 1)
    h2 = heading(font_name, 2)
    t = title(font_name)
    story: list = []

    diag = load_json("diagnostic.json")
    snap = load_json("latest_snapshot.json")
    desc = diag.get("describe", {})
    close_desc = desc.get("close", {})

    story += [
        Paragraph("股票数据诊断与技术指标分析", t),
        Paragraph("TASK2 作业报告", t),
        Spacer(1, 0.4 * cm),
    ]

    # ===== Q1 =====
    story.append(Paragraph("一、数据基础诊断分析", h1))
    for p in [
        f"本报告以中芯国际港股（00981.HK）近一年日线数据为对象，数据文件来自 task02_indicator_lab/data/raw/smic_hk_00981_daily.csv，共 {diag.get('rows', '—')} 条记录，区间 {diag.get('date_range', '—')}。",
        "（1）缺失值检查：对 date、open、high、low、close、volume、amount 等字段逐一统计缺失个数与占比。经检查，各字段缺失值均为 0，数据完整可用；重复交易日 0 条，不存在 high &lt; low 的异常价格记录。",
        f"（2）描述性统计：收盘价均值约 {close_desc.get('mean', 0):.2f} 港元，标准差 {close_desc.get('std', 0):.2f}，最小值 {close_desc.get('min', 0):.2f}，最大值 {close_desc.get('max', 0):.2f}，中位数 {close_desc.get('50%', close_desc.get('median', 0)):.2f}。成交量均值约 {desc.get('volume', {}).get('mean', 0):,.0f} 股，显示该区间股价波动与成交活跃度均处于较高水平。",
        "（3）诊断结论：数据质量良好，可直接用于指标计算。图1 展示收盘价分布与成交量时序，可见收盘价呈右偏分布（后期中枢抬升），成交量在部分时段出现明显放量。",
    ]:
        story.append(Paragraph(p, b))
        story.append(Spacer(1, 0.12 * cm))

    add_img(story, FIG / "fig1_diagnostic.png", "图1  中芯国际港股（00981）数据基础诊断", h2, h=6.5 * cm)
    story.append(Paragraph(
        "图1 解读：左图为收盘价直方图，红色虚线为均值线，可见价格主要集中在 40~90 港元区间，近期高价区样本增多；"
        "右图为成交量时序，2025 年末至 2026 年中出现数次放量高峰，与价格剧烈波动时段相对应，提示分析指标时需关注价量配合。",
        b,
    ))
    story.append(PageBreak())

    # ===== Q2 =====
    story.append(Paragraph("二、RSI、MACD、布林带指标的含义与计算方法", h1))

    story.append(Paragraph("（一）RSI（相对强弱指数）", h2))
    for p in [
        "作用：衡量一定周期内价格上涨力度与下跌力度的相对强弱，用于识别超买（涨势过强）与超卖（跌势过强）状态，属于动量类指标。",
        "计算方法（period 通常取 14，采用 Wilder 平滑）：① 计算每日 change = close_t − close_{t−1}；② gain = max(change, 0)，loss = max(−change, 0)；③ 对 gain、loss 分别做 Wilder 指数平滑；④ RS = avg_gain / avg_loss；⑤ RSI = 100 − 100 / (1 + RS)。RSI 取值 0~100，常用阈值 70（超买）与 30（超卖）。",
    ]:
        story.append(Paragraph(p, b))
        story.append(Spacer(1, 0.12 * cm))

    story.append(Paragraph("（二）MACD（指数平滑异同移动平均线）", h2))
    for p in [
        "作用：通过短期与长期指数移动平均线的差值反映趋势方向与动能变化，用于判断金叉/死叉及趋势强弱，属于趋势+动量复合指标。",
        "计算方法（常用参数 12, 26, 9）：① DIF = EMA(close, 12) − EMA(close, 26)；② DEA = EMA(DIF, 9)；③ MACD 柱 = DIF − DEA。DIF 上穿 DEA 称金叉（偏强），下穿称死叉（偏弱）；柱状图由负转正表示上涨动能增强。",
    ]:
        story.append(Paragraph(p, b))
        story.append(Spacer(1, 0.12 * cm))

    story.append(Paragraph("（三）布林带（Bollinger Bands）", h2))
    for p in [
        "作用：以移动平均线为中轨，上下加减若干倍标准差形成通道，描述价格相对均值的偏离程度与波动范围，用于判断相对高低与波动收敛/扩张。",
        "计算方法（常用参数 period=20, k=2）：① 中轨 mid = SMA(close, 20)；② 标准差 std = rolling_std(close, 20)；③ 上轨 upper = mid + 2×std；④ 下轨 lower = mid − 2×std。价格触及上轨偏强，触及下轨偏弱；带宽收窄（收口）常预示后续波动可能放大。",
    ]:
        story.append(Paragraph(p, b))
        story.append(Spacer(1, 0.12 * cm))

    story.append(PageBreak())

    # ===== Q3 =====
    story.append(Paragraph("三、Python 编程实现与可视化", h1))
    for p in [
        "实现文件：TASK2/task2_analysis.py，指标算法与 task02_indicator_lab/scripts/indicators.py 一致。",
        "（1）加载数据：使用 pandas.read_csv 读取已存储 CSV，转换 date 为 datetime 并排序。",
        "（2）计算指标：调用 compute_rsi、compute_macd、compute_bollinger 分别计算 RSI(14)、MACD(12,26,9)、布林带(20,2)。",
        "（3）可视化：使用 matplotlib 绘制图2~图4，Mac 环境配置 Songti/PingFang 中文字体。",
        f"最新一日（{snap.get('date', '—')}）指标读数：收盘 {snap.get('close', '—')} 港元，RSI={snap.get('rsi_14', '—')}，"
        f"DIF={snap.get('macd_dif', '—')}，DEA={snap.get('macd_dea', '—')}，柱={snap.get('macd_hist', '—')}，"
        f"布林中轨={snap.get('boll_mid', '—')} 港元。",
    ]:
        story.append(Paragraph(p, b))
        story.append(Spacer(1, 0.12 * cm))

    add_img(story, FIG / "fig2_boll.png", "图2  中芯国际港股（00981）收盘价与布林带(20,2)", h2)
    story.append(Paragraph(
        f"图2 解读：收盘价 {snap.get('date', '')} 报 {snap.get('close', '—')} 港元，位于中轨 {snap.get('boll_mid', '—')} 港元附近偏下。"
        "2025 年下半年以来价格多次触及或突破上轨，显示强势阶段；近期回调至中轨下方，需关注能否在中轨获得支撑。",
        b,
    ))
    story.append(Spacer(1, 0.12 * cm))

    add_img(story, FIG / "fig3_rsi.png", "图3  中芯国际港股（00981）RSI(14)", h2, h=5.5 * cm)
    story.append(Paragraph(
        f"图3 解读：最新 RSI={snap.get('rsi_14', '—')}，处于 30~70 中性区间，未出现明显超买/超卖。"
        "2025 年 10 月前后 RSI 曾多次接近或超过 70，与当时价格急升相对应；当前读数回落，反映上涨动能有所减弱。",
        b,
    ))
    story.append(Spacer(1, 0.12 * cm))

    add_img(story, FIG / "fig4_macd.png", "图4  中芯国际港股（00981）MACD(12,26,9)", h2, h=8 * cm)
    story.append(Paragraph(
        f"图4 解读：DIF={snap.get('macd_dif', '—')}，DEA={snap.get('macd_dea', '—')}，柱={snap.get('macd_hist', '—')}。"
        "DIF 略高于 DEA 且柱为正但幅度很小，短期动能略偏多但不够强劲；2026 年 5 月前后 MACD 柱显著放大，与价格主升浪同步。",
        b,
    ))
    story.append(PageBreak())

    # ===== Q4 =====
    story.append(Paragraph("四、扩展指标：ATR（平均真实波幅）", h1))
    for p in [
        "除 RSI、MACD、布林带外，技术分析中还有大量典型指标，例如：KDJ（随机指标）、OBV（能量潮）、CCI（顺势指标）、SAR（抛物线转向）、ATR（平均真实波幅）、威廉指标 %R 等。",
        "本报告选取 ATR 进行扩展介绍与计算。ATR 由 Welles Wilder 提出，衡量价格平均波动幅度，不表示涨跌方向，常用于止损设置与仓位管理。",
        "计算方法（period 通常取 14，Wilder 平滑）：① TR = max(high−low, |high−close_{t−1}|, |low−close_{t−1}|)；② ATR = Wilder_smooth(TR, 14)。",
        f"图5 为 ATR(14) 走势。最新 ATR={snap.get('atr_14', '—')} 港元，意味着近期日均波动约 {snap.get('atr_14', 0):.2f} 港元；"
        f"若以 2×ATR 作为止损宽度参考，约为 {2 * snap.get('atr_14', 0):.2f} 港元。2026 年 5 月 ATR 明显抬升，与价格剧烈波动阶段一致。",
        "其他指标简介：KDJ 侧重短期超买超卖；OBV 通过成交量确认趋势；CCI 衡量价格偏离统计均值的程度。ATR 的独特价值在于量化「波动有多大」，是风险管理的重要工具。",
    ]:
        story.append(Paragraph(p, b))
        story.append(Spacer(1, 0.12 * cm))

    add_img(story, FIG / "fig5_atr.png", "图5  中芯国际港股（00981）ATR(14) 扩展指标", h2, h=5.5 * cm)
    story.append(Paragraph(
        "图5 解读：ATR 上升表示市场波动加剧，下降表示波动收敛。当前 ATR 处于中等偏高水平，操作时应预留足够价格缓冲空间。"
        "声明：以上分析基于历史数据与技术指标，仅供课程学习，不构成任何投资建议。",
        b,
    ))

    return story


def main():
    ensure_figures()
    fn = register_font()
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4,
                            leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2.5*cm, bottomMargin=2.5*cm)
    doc.build(build_story(fn))
    print(f"PDF 已生成: {OUTPUT}")


if __name__ == "__main__":
    main()
