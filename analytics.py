#!/usr/bin/env python3
"""访问量采集与报告生成。通过不蒜子 API 获取 PV/UV，保存历史数据，生成 HTML 报告。"""

import json, os, sys, re
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request

TZ = timezone(timedelta(hours=8))
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(OUTPUT_DIR, "analytics_data.json")
REPORT_FILE = os.path.join(OUTPUT_DIR, "analytics_report.html")
SITE_URL = "https://2026-world-cup-838.pages.dev"


def fetch_busuanzi() -> tuple:
    """返回 (site_pv, site_uv)。"""
    url = "https://busuanzi.ibruce.info/busuanzi?jsonpCallback=cb"
    req = Request(url, headers={"Referer": SITE_URL, "User-Agent": "Marvis-Analytics/1.0"})
    with urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
    m = re.search(r'"site_pv":(\d+).*"site_uv":(\d+)', body)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


def load_history():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"records": []}


def save_history(h):
    with open(DATA_FILE, "w") as f:
        json.dump(h, f, ensure_ascii=False, indent=2)


def generate_report(history, site_pv, site_uv):
    records = history.get("records", [])
    today_str = datetime.now(TZ).strftime("%Y-%m-%d")

    if not records:
        daily = []
        day_count = 0
        yesterday_pv = 0
    else:
        daily = []
        prev_pv = records[0].get("pv", 0)
        for r in records:
            pv = r.get("pv", 0)
            uv = r.get("uv", 0)
            daily.append({"date": r["date"], "pv": pv, "uv": uv, "delta_pv": pv - prev_pv, "delta_uv": uv - prev_pv})
            prev_pv = pv
        day_count = len(records)
        yesterday_pv = daily[-1]["delta_pv"] if day_count >= 1 else 0

    rows = ""
    for d in reversed(daily):
        rows += f"<tr><td>{d['date']}</td><td>+{d['delta_pv']}</td><td>+{d['delta_uv']}</td><td>{d['pv']}</td><td>{d['uv']}</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>2026 世界杯网页 · 访问量报告</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background:#0a0e27; color:#e0e0e0; min-height:100vh; }}
  .container {{ max-width:900px; margin:0 auto; padding:40px 20px; }}
  h1 {{ font-size:2rem; margin-bottom:8px; background: linear-gradient(135deg,#00d2ff,#3a7bd5); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
  .subtitle {{ color:#888; margin-bottom:32px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-bottom:32px; }}
  .card {{ background:rgba(255,255,255,0.05); border-radius:12px; padding:24px; border:1px solid rgba(255,255,255,0.08); text-align:center; }}
  .card .label {{ font-size:0.85rem; color:#888; margin-bottom:8px; }}
  .card .value {{ font-size:2.2rem; font-weight:700; background:linear-gradient(135deg,#00d2ff,#3a7bd5); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
  table {{ width:100%; border-collapse:collapse; margin-bottom:16px; }}
  th, td {{ padding:10px 14px; text-align:center; border-bottom:1px solid rgba(255,255,255,0.06); }}
  th {{ color:#888; font-weight:500; font-size:0.85rem; }}
  td {{ font-size:0.95rem; }}
  .footer {{ text-align:center; color:#555; font-size:0.8rem; margin-top:40px; }}
  .link {{ color:#00d2ff; }}
</style>
</head>
<body>
<div class="container">
  <h1>2026 世界杯网页 · 访问量报告</h1>
  <p class="subtitle">报告生成时间：{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}（北京时间）</p>

  <div class="cards">
    <div class="card">
      <div class="label">累计 PV</div>
      <div class="value">{site_pv:,}</div>
    </div>
    <div class="card">
      <div class="label">累计 UV</div>
      <div class="value">{site_uv:,}</div>
    </div>
    <div class="card">
      <div class="label">昨日 PV</div>
      <div class="value">{yesterday_pv:,}</div>
    </div>
    <div class="card">
      <div class="label">统计天数</div>
      <div class="value">{day_count}</div>
    </div>
  </div>

  <table>
    <thead><tr><th>日期</th><th>当日 PV 增量</th><th>当日 UV 增量</th><th>累计 PV</th><th>累计 UV</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <p class="footer">
    数据来源：<a class="link" href="https://busuanzi.ibruce.info">不蒜子</a> · 
    每 24 小时自动采集 · 
    网页地址：<a class="link" href="{SITE_URL}">{SITE_URL}</a>
  </p>
</div>
</body>
</html>"""

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    return html


def collect():
    pv, uv = fetch_busuanzi()
    history = load_history()
    today = datetime.now(TZ).strftime("%Y-%m-%d")

    records = history.get("records", [])
    if records and records[-1]["date"] == today:
        records[-1]["pv"] = pv
        records[-1]["uv"] = uv
        records[-1]["time"] = datetime.now(TZ).strftime("%H:%M")
    else:
        records.append({
            "date": today,
            "time": datetime.now(TZ).strftime("%H:%M"),
            "pv": pv,
            "uv": uv
        })
    history["records"] = records
    history["last_updated"] = datetime.now(TZ).isoformat()
    save_history(history)
    return history, pv, uv


if __name__ == "__main__":
    history, pv, uv = collect()
    generate_report(history, pv, uv)
    print(f"采集完成：PV={pv:,}  UV={uv:,}  报告 → {REPORT_FILE}")
