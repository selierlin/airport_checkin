#!/usr/bin/env python3
import json
import sys
import os

from panels import get_panel
from notify import send_qywx


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if not os.path.exists(config_path):
        print("配置文件不存在，请根据 config-template.json 创建 config.json")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run():
    cfg = load_config()
    accounts = cfg.get("accounts", [])
    notify_cfg = cfg.get("notify", {})

    if not accounts:
        print("没有配置任何账户")
        return

    all_results = []
    for account in accounts:
        panel_cls = get_panel(account.get("panel", "v2board"))
        panel = panel_cls(account)
        result = panel.run()
        print(result)
        print()
        all_results.append(result)

    # 发送通知
    if notify_cfg.get("enabled"):
        send_qywx(notify_cfg.get("qywx_key"), "\n".join(all_results))


if __name__ == "__main__":
    run()
