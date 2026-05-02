import re
from urllib.parse import urlparse
from .sspanel import SSPanel


class Renzhe(SSPanel):
    """忍者云 (renzhe.cloud) — SSPanel Malio 主题，覆盖 HTML 解析

    Cloudflare 防护需要 curl_cffi 模拟浏览器指纹，无需手动 cf_clearance。
    """

    def __init__(self, account: dict):
        # 跳过 SSPanel.__init__，直接用 BasePanel 的初始化
        super(SSPanel, self).__init__(account)

        from curl_cffi import requests as cf_requests

        self.session = cf_requests.Session(impersonate="chrome")
        if self._proxies():
            self.session.proxies = self._proxies()

        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.base_url + "/",
            "Origin": self.base_url,
        })

    def get_user_info(self) -> dict:
        result = {}
        try:
            resp = self.session.get(self.base_url + "/user", timeout=15)
            self._parse_user_page(result, resp.text)
        except Exception as e:
            print(f"[{self.name}] 获取用户信息失败: {e}")

        # 邀请页：返利比例
        try:
            resp = self.session.get(self.base_url + "/user/invite", timeout=15)
            m = re.search(r"<b>(\d+)%</b>\s*的返利", resp.text)
            if m:
                result["返利比例"] = "{}%".format(m.group(1))
        except Exception:
            pass

        return result

    def _parse_user_page(self, result: dict, html: str):
        # 钱包余额: ¥ <span class="counter">531.95</span>
        m = re.search(r"钱包余额.*?¥\s*<span class=\"counter\">([\d.]+)</span>", html, re.DOTALL)
        if m:
            result["余额"] = "¥{}".format(m.group(1))

        # 剩余流量: dashboard-stat-value"> 81.55GB
        m = re.search(r"剩余流量.*?dashboard-stat-value\">\s*([\d.]+)\s*(GB|TB|MB)", html, re.DOTALL)
        if m:
            result["剩余流量"] = "{} {}".format(m.group(1), m.group(2))

        # 会员时长: <span class="counter">0</span><span class="unit">天</span>
        m = re.search(r"会员时长.*?<span class=\"counter\">([\d.]+)</span><span class=\"unit\">天", html, re.DOTALL)
        if m:
            days = m.group(1)
            # 检查状态
            idx = html.find("会员时长")
            snippet = html[idx : idx + 500]
            if "已过期" in snippet or "danger" in snippet:
                result["会员状态"] = "已过期"
            else:
                result["会员时长"] = "{} 天".format(days)

        # 累计获得奖励金额：¥1647.34
        m = re.search(r"累计获得奖励金额：¥([\d.]+)", html)
        if m:
            result["累计奖励"] = "¥{}".format(m.group(1))
