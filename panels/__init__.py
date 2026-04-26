from .v2board import V2Board
from .sspanel import SSPanel
from .bygcloud import Bygcloud
from .wmsxwd import Wmsxwd
from .fatcatcf import Fatcatcf

PANEL_MAP = {
    "v2board": V2Board,
    "sspanel": SSPanel,
    "bygcloud": Bygcloud,
    "wmsxwd": Wmsxwd,
    "fatcatcf": Fatcatcf,
}


def get_panel(panel_type: str):
    cls = PANEL_MAP.get(panel_type)
    if not cls:
        raise ValueError(f"不支持的面板类型: {panel_type}，当前支持: {list(PANEL_MAP.keys())}")
    return cls
