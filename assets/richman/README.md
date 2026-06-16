# 大富翁美术资源

旗舰大富翁使用 **CC0 / 开源可商用** 素材 + 程序生成兜底。

## 快速准备

```bash
# 1) 程序生成占位纹理
python scripts/generate_richman_assets.py

# 2) 下载城市地标照片（Pexels，需网络）
python scripts/download_city_images.py

# 3) 下载 Kenney CC0 棋盘素材（需网络）
python scripts/download_richman_assets.py
```

## 已对接的开源参考

| 来源 | 用途 | 许可 |
|------|------|------|
| [florandefossez/monopoly](https://github.com/florandefossez/monopoly) | 机会/命运卡 **数据结构**（earn/pay/goto/jail 等） | 仓库 MIT；**棋盘图属于 Hasbro，未使用** |
| [Kenney Board Game Kit](https://kenney.nl/assets/board-game-kit) | 骰子、棋子、板块贴图 | **CC0** |
| [Kytric Voxel Board Games](https://kytric.itch.io/board-game-assets) | 可选 3D 棋子/骰子 GLTF | **CC0** |
| [Poly Haven](https://polyhaven.com/) | PBR 地面/建筑纹理 | **CC0** |

## 目录

```
textures/     — 2D 贴图（Kenney + 生成）
models/       — 预留 GLTF（M3）
cards/        — 预留卡面图
```

## 规则说明

当前 M2 已实现经典要素：

- 机会 / 命运 **完整卡池**（各 16 张，中文）
- **同色垄断** 双倍地租、**盖房**（最高酒店）
- **监狱** / 进监狱格 / 保释 / 出狱许可
- 过起点 ¥2000、破产出局

M3 计划：40 格标准棋盘、GLTF 建筑、音效、网络 CC0 场景包。

## 许可记录

使用新素材时在此追加一行：

```
YYYY-MM-DD  素材名  URL  许可证
```
