import requests


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
