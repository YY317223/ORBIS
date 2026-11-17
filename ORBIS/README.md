# ORBIS · 从太空看地球

一个纯前端 Three.js 3D 地球数据可视化 + 纯标准库 Python 后端的数据服务。
本文件夹已按"前端 / 后端分离"整理好，开箱即跑。

## 目录结构

```
ORBIS/
├── README.md              # 本说明
├── orbis.html            # 前端成品（单文件，双击即可在浏览器打开）
├── data.js               # 指标数据（前端页面 + 后端邮件中文名共用）
├── frontend/             # 前端源码与构建
│   ├── globe_template.html   # 手写前端源码（3196 行，Three.js 全部逻辑）
│   ├── build_globe.py        # 把模板 + three.js + 贴图 + 数据打包成 orbis.html
│   └── globe_assets/         # three.min.js 与地球贴图
└── backend/              # 后端服务（纯标准库，无第三方依赖）
    ├── app.py                # 主服务：HTTP / gzip / 状态灯 / 订阅退订 / 数据推送
    ├── mailer.py             # 邮件发送（有 SMTP 发信，没有则落 outbox/*.eml）
    ├── fetch_wb.py           # 从世界银行 API 拉取 GDP/人口/人均/寿命
    ├── config.example.json   # SMTP 配置示例
    ├── start.bat / start.sh  # Windows / macOS·Linux 一键启动
    └── data/                 # 运行时数据目录（wb.json / subs.db，自动生成）
```

> 设计说明：`orbis.html` 和 `data.js` 放在根目录，是因为后端 `app.py`
> 默认 serve"上一级目录的 orbis.html"。前端构建脚本也按"上一级"找 `data.js`
> 并把成品写到"上一级"。这样前后端无需改任何路径即可联动。

## 前端

- **直接看效果**：双击根目录 `orbis.html` 即可（已内联 three.js、数据、贴图）。
- **改源码后重新打包**：
  ```bash
  cd frontend
  python3 build_globe.py        # 读取 globe_template.html + globe_assets + ../data.js
                                # 输出到 ../orbis.html
  ```
  想用 8K 极致贴图：`ORBIS_TEX=8k python3 build_globe.py`（页面体积会变大）。

## 后端

```bash
cd backend
cp config.example.json config.json   # 可选：填入 SMTP 信息才真发邮件

# 本地运行（自动起抓取线程 + 开浏览器）
./start.sh            # macOS / Linux
start.bat             # Windows

# 公网部署
HOST=0.0.0.0 PORT=8080 python3 app.py
```

启动后访问 `http://127.0.0.1:8765`（本地）或 `http://<服务器IP>:8080`（公网）。
后端会自动把根目录的 `orbis.html` 作为页面发出去，并提供：
`/api/status`（状态灯）、`/api/wb`（最新数据）、`/api/subscribe`、`/api/unsubscribe`。

### 邮件
- 不配 `config.json`：订阅确认信 / 提醒信会写进 `backend/data/outbox/*.eml`，不会真发出去。
- 配了 SMTP：通过 `config.json` 里的 `smtp` 字段发送，并自动带上
  `List-Unsubscribe` 标准退订头。

## 备注
- 后端每 12 小时检查一次世界银行数据；也可 `python3 app.py --once` 挂系统计划任务。
- 当前线上实例：http://8.137.183.172:8080 （部署目录 `/opt/orbis`，结构同本文件夹）。
