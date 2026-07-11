"""参数网格扫描器：对策略参数做笛卡尔积搜索并排序。"""

from __future__ import annotations

import json
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .spec_runner import build_engine, load_stock_df, run_one, stock_index


def expand_param_grid(param_grid: dict[str, list], constraints: list[dict]) -> list[dict]:
    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]
    combos: list[dict] = []
    for combo in product(*values):
        params = dict(zip(keys, combo))
        ok = True
        for c in constraints:
            if c.get("rule") == "short < long":
                if params.get("short", 0) >= params.get("long", 0):
                    ok = False
                    break
        if ok:
            combos.append(params)
    return combos


class ParameterScanner:
    """按 spec.param_scan 配置执行网格搜索。"""

    def __init__(self, spec: dict, base_dir: Path):
        self.spec = spec
        self.base_dir = base_dir
        self.engine = build_engine(spec)
        self.stocks = stock_index(spec)

    def run(self, scan_cfg: dict) -> dict[str, Any]:
        stock_id = scan_cfg["stock_id"]
        strategy_type = scan_cfg.get("strategy", "dual_ma")
        if isinstance(strategy_type, dict):
            strategy_type = strategy_type.get("type", "dual_ma")

        stock = self.stocks[stock_id]
        df = load_stock_df(self.base_dir, stock, self.spec)

        strategy_entry = self.spec["strategies"].get(strategy_type, {})
        constraints = scan_cfg.get("constraints") or strategy_entry.get("constraints", [])
        param_grid = scan_cfg["param_grid"]
        rank_by = scan_cfg.get("rank_by", "sharpe_ratio")
        ascending = scan_cfg.get("rank_ascending", False)
        top_n = int(scan_cfg.get("top_n", 10))

        combos = expand_param_grid(param_grid, constraints)
        rows: list[dict] = []

        print(f"\n参数扫描: {stock['name']}({stock['code']}) · {strategy_type}")
        print(f"  网格组合: {len(combos)} 组")

        for params in combos:
            sid = self._scenario_id(stock_id, params)
            try:
                r = run_one(
                    self.engine,
                    df,
                    stock,
                    strategy_type,
                    params,
                    self.spec,
                    scenario_id=sid,
                    batch_id="param_scan",
                )
                m = r["metrics"]
                rows.append(
                    {
                        "scenario_id": sid,
                        "stock_id": stock_id,
                        "stock_name": stock["name"],
                        "code": stock["code"],
                        "strategy": r["strategy"],
                        **params,
                        **m,
                    }
                )
            except ValueError as e:
                rows.append(
                    {
                        "scenario_id": sid,
                        "stock_id": stock_id,
                        "error": str(e),
                        **params,
                    }
                )

        table = pd.DataFrame(rows)
        if rank_by in table.columns and len(table):
            table = table.sort_values(rank_by, ascending=ascending, na_position="last")

        best = table.iloc[0].to_dict() if len(table) else {}
        top = table.head(top_n).to_dict(orient="records")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_cfg = scan_cfg.get("output", {})
        base_out = self.base_dir / self.spec["defaults"]["output"]["base_dir"]
        base_out.mkdir(parents=True, exist_ok=True)

        csv_name = out_cfg.get("scan_csv", "scan_{timestamp}.csv").format(timestamp=ts)
        json_name = out_cfg.get("scan_json", "scan_{timestamp}.json").format(timestamp=ts)
        csv_path = base_out / csv_name
        json_path = base_out / json_name
        table.to_csv(csv_path, index=False, encoding="utf-8")

        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stock_id": stock_id,
            "strategy": strategy_type,
            "param_grid": param_grid,
            "combinations": len(combos),
            "rank_by": rank_by,
            "best": best,
            "top_n": top,
        }
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        heatmap_path = None
        if scan_cfg.get("save_heatmap", True) and "short" in param_grid and "long" in param_grid:
            heatmap_path = self._save_heatmap(
                table,
                stock,
                rank_by,
                base_out / out_cfg.get("heatmap_png", "scan_heatmap_{stock_id}_{timestamp}.png").format(
                    stock_id=stock_id, timestamp=ts
                ),
            )
            report["heatmap"] = str(heatmap_path)

        print(f"  扫描 CSV: {csv_path}")
        print(f"  扫描 JSON: {json_path}")
        if heatmap_path:
            print(f"  热力图: {heatmap_path}")
        if best:
            print(
                f"  最优 [{rank_by}]: MA{best.get('short')}/{best.get('long')} → "
                f"回报={best.get('cumulative_return_pct')}% "
                f"MDD={best.get('max_drawdown_pct')}% "
                f"Sharpe={best.get('sharpe_ratio')}"
            )

        return {"table": table, "report": report, "csv_path": csv_path, "json_path": json_path}

    @staticmethod
    def _scenario_id(stock_id: str, params: dict) -> str:
        parts = "_".join(f"{k}{v}" for k, v in sorted(params.items()))
        return f"scan_{stock_id}_{parts}"

    @staticmethod
    def _save_heatmap(
        table: pd.DataFrame,
        stock: dict,
        metric: str,
        out_path: Path,
    ) -> Path | None:
        sub = table.dropna(subset=[metric, "short", "long"])
        if sub.empty:
            return None

        pivot = sub.pivot(index="long", columns="short", values=metric)
        pivot = pivot.sort_index(ascending=True)

        try:
            from matplotlib import font_manager
            from matplotlib.font_manager import FontProperties

            fp = None
            for path in (
                "/System/Library/Fonts/Supplemental/Songti.ttc",
                "/System/Library/Fonts/PingFang.ttc",
            ):
                if Path(path).exists():
                    fp = FontProperties(fname=path, size=11)
                    break
        except Exception:
            fp = None

        fig, ax = plt.subplots(figsize=(8, 5))
        im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn", origin="lower")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([str(c) for c in pivot.columns])
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels([str(i) for i in pivot.index])
        ax.set_xlabel("MA short")
        ax.set_ylabel("MA long")
        title = f"{stock['name']}({stock['code']}) {metric} heatmap"
        if fp:
            ax.set_title(title, fontproperties=fp)
        else:
            ax.set_title(title)

        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                val = pivot.values[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8, color="black")

        fig.colorbar(im, ax=ax, shrink=0.8)
        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out_path
