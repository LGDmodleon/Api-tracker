#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API供应商排行榜数据采集系统
从 hvoy.ai 采集 fable5, opus48, opus46, gpt55 四个模型的每日前10名供应商
累积统计每个供应商进入排行榜的次数，生成可视化网站数据
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DAILY_DIR = os.path.join(DATA_DIR, "daily")
SITE_DIR = os.path.join(BASE_DIR, "site")
SUMMARY_FILE = os.path.join(DATA_DIR, "summary.json")
DATA_JS_FILE = os.path.join(SITE_DIR, "data.js")

LEADERBOARD_URL = "https://hvoy.ai/__leaderboard"
TOP_N = 10  # 每个模型取前N名

# 目标模型配置
MODELS = {
    "fable5": {
        "key": "fable5",
        "displayName": "Claude Fable 5",
        "color": "#A78BFA",
        "icon": "sparkles"
    },
    "opus48": {
        "key": "opus48",
        "displayName": "Claude Opus 4.8",
        "color": "#60A5FA",
        "icon": "zap"
    },
    "opus46": {
        "key": "opus46",
        "displayName": "Claude Opus 4.6",
        "color": "#34D399",
        "icon": "shield"
    },
    "gpt55": {
        "key": "gpt55",
        "displayName": "GPT-5.5",
        "color": "#FBBF24",
        "icon": "bot"
    }
}


def ensure_dirs():
    """确保必要的目录存在"""
    for d in [DATA_DIR, DAILY_DIR, SITE_DIR]:
        os.makedirs(d, exist_ok=True)


def load_json(filepath):
    """安全加载JSON文件"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  [警告] 无法解析 {filepath}: {e}")
        return None


def save_json(filepath, data):
    """保存JSON文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_leaderboard():
    """从 hvoy.ai 获取排行榜数据"""
    print(f"  → 请求 {LEADERBOARD_URL} ...")
    req = urllib.request.Request(
        LEADERBOARD_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            return data
    except urllib.error.URLError as e:
        print(f"  [错误] 网络请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"  [错误] JSON解析失败: {e}")
        return None


def get_beijing_date():
    """获取北京时间日期字符串"""
    beijing = timezone(timedelta(hours=8))
    return datetime.now(beijing).strftime("%Y-%m-%d")


def get_beijing_time():
    """获取北京时间ISO格式字符串"""
    beijing = timezone(timedelta(hours=8))
    return datetime.now(beijing).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def create_empty_summary():
    """创建空的summary结构"""
    models_data = {}
    for key, cfg in MODELS.items():
        models_data[key] = {
            "displayName": cfg["displayName"],
            "color": cfg["color"],
            "vendors": {}
        }
    return {
        "updatedAt": "",
        "lastFetchDate": "",
        "totalDaysTracked": 0,
        "trackedDates": [],
        "models": models_data
    }


def update_summary(api_data, summary):
    """用新的API数据更新summary"""
    now_beijing = get_beijing_time()
    today = get_beijing_date()

    # 更新元数据
    summary["updatedAt"] = now_beijing
    summary["lastFetchDate"] = today

    if today not in summary["trackedDates"]:
        summary["trackedDates"].append(today)
    summary["totalDaysTracked"] = len(summary["trackedDates"])

    channel_stats = api_data.get("channelStats", {})
    total_new = 0
    new_vendors = 0

    for model_key, model_cfg in MODELS.items():
        models_data = summary["models"][model_key]
        vendors = models_data["vendors"]

        # 获取该模型的排行榜数据
        entries = channel_stats.get(model_key, [])
        if not entries:
            print(f"    {model_cfg['displayName']}: 无数据")
            continue

        # 取前TOP_N名
        top_entries = entries[:TOP_N]
        model_count = 0

        for rank, entry in enumerate(top_entries, 1):
            relay_id = str(entry.get("relaySiteId", ""))
            if not relay_id:
                continue

            site_name = entry.get("site", "")
            site_domain = entry.get("siteDomain", "")
            channel = entry.get("channel", "")
            display_name = entry.get("displayName", "")
            site_url = entry.get("siteUrl", "")
            pass_rate = entry.get("passRate")
            online_rate = entry.get("onlineRate")
            error_rate = entry.get("errorRate")
            avg_latency = entry.get("avgLatencyS")
            latest_price = entry.get("latestInputPriceCny")
            verification_type = entry.get("verificationType", "")
            token_ratio = entry.get("tokenUsageRatio")
            sample_count = entry.get("sampleCount")

            # 构建appearance记录
            appearance = {
                "date": today,
                "rank": rank,
                "passRate": pass_rate,
                "onlineRate": online_rate,
                "errorRate": error_rate,
                "avgLatencyS": avg_latency,
                "latestInputPriceCny": latest_price,
                "tokenUsageRatio": token_ratio,
                "sampleCount": sample_count
            }

            if relay_id in vendors:
                # 更新已有供应商
                v = vendors[relay_id]
                v["appearances"].append(appearance)
                v["totalAppearances"] = len(v["appearances"])
                v["bestRank"] = min(v["bestRank"], rank)
                v["worstRank"] = max(v.get("worstRank", 0), rank)
                v["latestPassRate"] = pass_rate
                v["latestOnlineRate"] = online_rate
                v["latestAvgLatencyS"] = avg_latency
                v["latestInputPriceCny"] = latest_price
                v["lastSeen"] = today
            else:
                # 新供应商
                vendors[relay_id] = {
                    "relaySiteId": relay_id,
                    "site": site_name,
                    "siteDomain": site_domain,
                    "channel": channel,
                    "displayName": display_name,
                    "siteUrl": site_url,
                    "verificationType": verification_type,
                    "appearances": [appearance],
                    "totalAppearances": 1,
                    "bestRank": rank,
                    "worstRank": rank,
                    "latestPassRate": pass_rate,
                    "latestOnlineRate": online_rate,
                    "latestAvgLatencyS": avg_latency,
                    "latestInputPriceCny": latest_price,
                    "firstSeen": today,
                    "lastSeen": today
                }
                new_vendors += 1

            model_count += 1

        total_new += model_count
        print(f"    {model_cfg['displayName']}: 收录 {model_count} 个供应商")

    print(f"  共新增 {total_new} 条记录，{new_vendors} 个新供应商")
    return summary


def generate_data_js(summary):
    """生成前端数据文件 data.js"""
    # 构建前端使用的数据结构
    frontend_data = {
        "updatedAt": summary["updatedAt"],
        "lastFetchDate": summary["lastFetchDate"],
        "totalDaysTracked": summary["totalDaysTracked"],
        "trackedDates": summary["trackedDates"],
        "models": {}
    }

    for model_key, model_cfg in MODELS.items():
        model_data = summary["models"][model_key]
        vendors_dict = model_data["vendors"]

        # 转换为数组并按 totalAppearances 降序排列
        vendors_list = list(vendors_dict.values())
        vendors_list.sort(key=lambda v: (-v["totalAppearances"], v["bestRank"]))

        # 计算总供应商数
        total_vendors = len(vendors_list)

        frontend_data["models"][model_key] = {
            "displayName": model_cfg["displayName"],
            "color": model_cfg["color"],
            "totalVendors": total_vendors,
            "vendors": vendors_list
        }

    js_content = f"""// 由 main.py 自动生成，请勿手动编辑
// 生成时间: {summary['updatedAt']}
// 追踪天数: {summary['totalDaysTracked']}
const LEADERBOARD_DATA = {json.dumps(frontend_data, ensure_ascii=False, indent=2)};
"""

    with open(DATA_JS_FILE, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"  → 已生成 {DATA_JS_FILE}")


def rebuild_summary():
    """从 daily/ 目录重建 summary.json"""
    print("  → 从 daily/ 目录重建 summary...")

    if not os.path.exists(DAILY_DIR):
        print("  [错误] daily/ 目录不存在")
        return None

    daily_files = sorted([
        f for f in os.listdir(DAILY_DIR)
        if f.endswith(".json")
    ])

    if not daily_files:
        print("  [警告] daily/ 目录为空")
        return create_empty_summary()

    summary = create_empty_summary()

    for filename in daily_files:
        filepath = os.path.join(DAILY_DIR, filename)
        api_data = load_json(filepath)
        if not api_data:
            continue

        date_str = filename.replace(".json", "")
        # 临时设置日期来正确更新trackedDates
        summary = update_summary(api_data, summary)

    save_json(SUMMARY_FILE, summary)
    print(f"  → 重建完成，共处理 {len(daily_files)} 天数据")
    return summary


def print_stats(summary):
    """打印统计摘要"""
    print()
    print("  ╔══════════════════════════════╗")
    print("  ║       数据统计摘要              ║")
    print("  ╚══════════════════════════════╝")
    print(f"  追踪天数: {summary['totalDaysTracked']}")
    print(f"  追踪日期: {', '.join(summary['trackedDates'][-7:])}")
    print()

    for model_key, model_cfg in MODELS.items():
        model_data = summary["models"][model_key]
        vendors = model_data["vendors"]
        if not vendors:
            print(f"  {model_cfg['displayName']}: 暂无数据")
            continue

        # 按出现次数排序
        sorted_vendors = sorted(
            vendors.items(),
            key=lambda x: (-x[1]["totalAppearances"], x[1]["bestRank"])
        )

        print(f"  {model_cfg['displayName']} Top 5 (按上榜次数):")
        for i, (vid, v) in enumerate(sorted_vendors[:5], 1):
            print(f"    {i}. {v['site']} ({v['channel']}) - "
                  f"上榜 {v['totalAppearances']} 次, "
                  f"最佳排名 #{v['bestRank']}, "
                  f"最新通过率 {v.get('latestPassRate', 'N/A')}%")
        print()


def main():
    """主函数"""
    # 设置控制台输出编码为UTF-8，避免Windows下中文乱码
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   API供应商排行榜数据采集系统             ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    ensure_dirs()

    # 检查是否是重建模式
    if len(sys.argv) > 1 and sys.argv[1] == "--rebuild":
        summary = rebuild_summary()
        if summary:
            save_json(SUMMARY_FILE, summary)
            generate_data_js(summary)
            print_stats(summary)
            print("  ✓ 重建完成！")
        else:
            print("  ✗ 重建失败！")
            sys.exit(1)
        return

    # 正常采集模式
    today = get_beijing_date()
    daily_file = os.path.join(DAILY_DIR, f"{today}.json")

    # 检查今天是否已采集
    if os.path.exists(daily_file) and len(sys.argv) <= 1:
        print(f"  [提示] {today} 的数据已存在，跳过采集。")
        print(f"  如需强制重新采集，请删除文件: {daily_file}")
        print(f"  或使用 --rebuild 从所有历史数据重建。")
        print()

        # 仍然重新生成 data.js（以防 summary 有变动）
        summary = load_json(SUMMARY_FILE)
        if summary:
            generate_data_js(summary)
            print_stats(summary)
        return

    # 1. 获取最新数据
    print(f"  [1/3] 采集最新数据 ({today})")
    api_data = fetch_leaderboard()
    if not api_data:
        print()
        print("  ✗ 数据采集失败！请检查网络连接。")
        print("    已有数据未被修改。")
        sys.exit(1)

    # 保存原始快照
    save_json(daily_file, api_data)
    print(f"  → 原始快照已保存: {daily_file}")

    # 2. 更新 summary
    print()
    print(f"  [2/3] 更新累积统计")
    summary = load_json(SUMMARY_FILE)
    if summary is None:
        print("  → 未找到 summary.json，创建新文件")
        summary = create_empty_summary()

    summary = update_summary(api_data, summary)
    save_json(SUMMARY_FILE, summary)

    # 3. 生成前端数据
    print()
    print(f"  [3/3] 生成网站数据")
    generate_data_js(summary)

    # 打印统计
    print_stats(summary)

    print("  ✓ 数据采集完成！")
    print()
    print(f"  网站文件: {os.path.join(SITE_DIR, 'index.html')}")
    print()


if __name__ == "__main__":
    main()
