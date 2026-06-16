"""城市/特殊格网络图源 — Pexels 免费可商用 + Wikimedia 备选"""
from __future__ import annotations

from typing import Dict, List, TypedDict


class ImageSource(TypedDict):
    urls: List[str]
    file: str
    license: str
    credit: str


def _pexels(photo_id: int, w: int = 640) -> str:
    return f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&w={w}"


CITY_IMAGE_SOURCES: Dict[str, ImageSource] = {
    "天津": {
        "urls": [_pexels(2570161)],
        "file": "tianjin.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "重庆": {
        "urls": [_pexels(417173), _pexels(2867275)],
        "file": "chongqing.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "上海": {
        "urls": [_pexels(1835718), _pexels(325933)],
        "file": "shanghai.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "南京": {
        "urls": [_pexels(2369853), _pexels(3490972)],
        "file": "nanjing.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "杭州": {
        "urls": [_pexels(2130078)],
        "file": "hangzhou.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "苏州": {
        "urls": [_pexels(913215)],
        "file": "suzhou.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "武汉": {
        "urls": [_pexels(3408354)],
        "file": "wuhan.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "成都": {
        "urls": [_pexels(145939)],
        "file": "chengdu.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "西安": {
        "urls": [_pexels(1546883)],
        "file": "xian.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "广州": {
        "urls": [_pexels(1366957)],
        "file": "guangzhou.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "深圳": {
        "urls": [_pexels(1188738), _pexels(466685)],
        "file": "shenzhen.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "北京": {
        "urls": [_pexels(7692220)],
        "file": "beijing.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "香港": {
        "urls": [_pexels(2901209)],
        "file": "hongkong.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "台北": {
        "urls": [_pexels(2387413)],
        "file": "taipei.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "起点": {
        "urls": [_pexels(2405844)],
        "file": "start.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "机会": {
        "urls": [_pexels(590020)],
        "file": "chance.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "命运": {
        "urls": [_pexels(207731)],
        "file": "fate.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "所得税": {
        "urls": [_pexels(259209)],
        "file": "tax.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "奢侈税": {
        "urls": [_pexels(259026)],
        "file": "luxury_tax.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "监狱": {
        "urls": [_pexels(977796)],
        "file": "jail.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "进监狱": {
        "urls": [_pexels(977796), _pexels(1626703)],
        "file": "go_jail.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
    "免费停车": {
        "urls": [_pexels(687757)],
        "file": "parking.jpg",
        "license": "Pexels License",
        "credit": "Pexels",
    },
}
