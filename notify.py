import time

import requests

# 企业微信机器人频率限制：每分钟20条，留余量用间隔3秒
SEND_INTERVAL = 3


def send_qywx(key: str, content: str):
    """发送企业微信机器人通知"""
    if not key or not content:
        return
    url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"
    resp = requests.post(url, json={
        "msgtype": "text",
        "text": {"content": content},
    })
    print(f"企业微信通知: {resp.json().get('errmsg', 'unknown')}")


def send_qywx_batch(key: str, messages: list[str]):
    """逐条发送多条消息，带间隔防止触发频率限制"""
    if not key or not messages:
        return
    for i, msg in enumerate(messages):
        send_qywx(key, msg)
        if i < len(messages) - 1:
            time.sleep(SEND_INTERVAL)
