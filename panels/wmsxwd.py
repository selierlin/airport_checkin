import re
from .sspanel import SSPanel


class Wmsxwd(SSPanel):
    """我們所嚮往的 — SSPanel Metron 主题"""

    def get_user_info(self) -> dict:
        result = {}
        try:
            resp = self.session.get(self.base_url + "/user", timeout=15)
            self._parse_user_page(result, resp.text)
        except Exception as e:
            print(f"[{self.name}] 获取用户信息失败: {e}")

        try:
            resp = self.session.get(self.base_url + "/user/setting/invite", timeout=15)
            self._parse_invite_page(result, resp.text)
        except Exception:
            pass

        return result

    def _parse_user_page(self, result: dict, html: str):
        """从 /user 页面 HTML 解析用户数据（Metron 主题）"""

        # 余额、流量、在线设备 — 共用模式: <div class="font-size-h4"><strong>VALUE</strong></div><p>LABEL</p>
        for label, key in [("钱包余额", "余额"), ("剩余流量", "剩余流量"), ("在线设备", "在线设备")]:
            m = re.search(
                r'font-size-h4[^>]*>\s*<strong>([^<]+)</strong>\s*</div>\s*<p[^>]*>' + label,
                html, re.DOTALL,
            )
            if m:
                val = re.sub(r'\s+', ' ', m.group(1).strip())
                result[key] = val

        # 会员时长/状态 — <span class="counter">VALUE</span>...<p>会员时长</p>
        m = re.search(r'counter[^>]*>([^<]+)</span>\s*</strong>\s*</div>\s*<p[^>]*>会员时长', html, re.DOTALL)
        if m:
            result["会员状态"] = m.group(1).strip()

        # 返利累计
        m = re.search(r'返利累计:\s*¥\s*([\d.]+)', html)
        if m:
            result["累计返利"] = "¥{}".format(m.group(1))

    def _parse_invite_page(self, result: dict, html: str):
        """从 /user/setting/invite 页面解析邀请数据"""

        # 返利余额 — <h3>返利余额</h3>...<strong>¥</strong>...<strong>59.72</strong>
        m = re.search(r'返利余额.*?<strong>¥</strong>\s*</span><strong>([^<]+)</strong>', html, re.DOTALL)
        if m:
            result["返利余额"] = "¥{}".format(m.group(1).strip())

        # 返利比例
        m = re.search(r'充值金额的[^<]*<code>(\d+)%</code>', html)
        if m:
            result["返利比例"] = "{}%".format(m.group(1))
