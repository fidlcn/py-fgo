# py-fgo — Windows FGO MuMu 自动化工具

`py-fgo` 是一套 **Windows 优先** 的 FGO 模拟器自动化工具，目标是在 **MuMu 模拟器** 中运行 **Fate/Grand Order**，通过 **ADB** 控制模拟器，通过 **OpenCV** 识别游戏界面，并由本地 **FastAPI** 服务和 **React** 管理界面统一调度任务。

> **边界说明**：本工具只做基于模拟器 UI 的自动化，也就是 ADB 截图和 ADB 输入。它不会修改游戏安装包，不会读写游戏内存，不会伪造网络请求，不会 Hook 游戏进程，也不会尝试绕过检测。实际使用可能违反游戏服务条款，账号风险需要自行评估。设计细节见 `doc/fgo_bot_design_plan.md` 和 `doc/ai_implementation_spec.md`。

## 目标运行环境

本软件目标运行环境是 **Windows**。

推荐环境：

- Windows 10/11
- MuMu 模拟器
- FGO 已安装并能在 MuMu 中正常运行
- ADB 可用，或者在 `configs/default.yaml` 中配置 ADB 路径
- Python 3.9+
- Node.js 18+

macOS/Linux 可以用于开发、阅读代码和跑部分测试，但真实运行目标是 Windows。原因是 MuMu 多开、模拟器窗口管理、桌面打包、托盘/开机启动、ADB 使用流程都更适合 Windows 环境。

## 当前默认体验：一键启动

普通用户路径尽量简化：

1. 在 Windows 上启动 MuMu。
2. 在 MuMu 中打开 FGO。
3. 进入支持的启动界面，建议停在关卡详情页。
4. 打开本工具的 Dashboard。
5. 点击 **Start**。

点击后，后端自动执行预检：

```text
扫描 ADB 设备
  -> 找到在线 MuMu 设备
  -> 检查前台 Android 包名是否是 FGO
  -> 截图
  -> 识别当前 FGO 界面
  -> 自动创建缺失的默认配置
  -> 创建任务并启动
```

支持的一键启动界面：

- `QUEST_DETAIL`：关卡详情页
- `SUPPORT_SELECT`：助战选择页
- `PARTY_CONFIRM`：队伍确认页

如果预检失败，界面会显示明确错误，而不是盲目点击：

- `NO_ADB_DEVICE`：没有检测到在线 ADB 设备。
- `FGO_NOT_RUNNING`：检测到模拟器，但 FGO 不是前台应用。
- `UNSUPPORTED_START_STATE`：FGO 已打开，但当前界面不适合启动任务。

## 架构

```text
Windows 桌面壳（计划：.NET 8 WebView2）
  -> 启动 FastAPI 后端
  -> 打开 React UI
  -> 管理托盘、开机启动、进程生命周期

React + TypeScript UI  --HTTP/WS-->  FastAPI 后端  --线程-->  每个模拟器一个 Python Worker
                                           | SQLite                    |- ADBClient
                                           | EventBus                  |- ScreenshotProvider
                                           |- TaskManager              |- VisionDetector (OpenCV)
                                                                      |- QuestRunner / StateMachine
                                                                      |- BattleExecutor + CardPolicy
                                                                      |- SupportSelector / RecoveryHandler
```

当前 MVP 可以不依赖 .NET 桌面壳，先按下面方式运行：

```text
FastAPI 后端 + React Dashboard + Python Worker + SQLite
```

后续 Windows 桌面壳应复用同一套本地 Web UI，而不是重新做一套界面。

## 关键设计选择

- **Windows 优先**：真实运行环境按 Windows 设计。
- **ADB 优先**：所有模拟器控制通过 `adb -s <device_id>` 隔离，适合多实例。
- **一键启动**：普通用户默认只需要打开 MuMu/FGO，然后点 Start。
- **高级配置后置**：战斗方案、助战筛选、AP 恢复、模板诊断、坐标校准放到高级页面。
- **配置化战斗方案**：波次 -> 回合 -> 动作 -> 选卡策略。
- **安全暂停/停止**：Worker 在安全点响应 pause/stop，不强杀线程。
- **MVP 从当前关卡开始**：自动日常本导航放到后续阶段。

## 目录结构

```text
backend/             FastAPI 应用、配置、日志、错误、事件、数据库、服务、API 路由
worker/              ADB、截图、MuMu 辅助、运行时、图像识别、FGO 自动化逻辑
frontend/            Vite + React + TypeScript 管理界面
configs/             default.yaml 配置文件
assets/templates/    OpenCV 模板图片，按 common/ quest/ support/ battle/ recovery/ 分组
data/                app.db 运行时数据库
logs/                fgobot.log 和截图目录
scripts/             Windows 和开发启动/构建脚本
tests/               pytest 单元测试、集成测试、Worker 测试
doc/                 设计方案和 AI 实现规格
plan/                规划记录
```

## Windows 安装

先安装 Python 和 Node.js，然后在 PowerShell 中执行：

```powershell
# 后端 / Worker
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 前端
cd frontend
npm install
cd ..
```

如果 PowerShell 阻止虚拟环境激活，可以先执行一次：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Windows 开发运行

推荐：

```powershell
.\scripts\start-dev.ps1
```

也可以手动开两个终端：

```powershell
# 终端 1：后端
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8765
```

```powershell
# 终端 2：前端
cd frontend
npm run dev
```

访问地址：

- Dashboard：<http://127.0.0.1:5173>
- API 文档：<http://127.0.0.1:8765/docs>
- 健康检查：<http://127.0.0.1:8765/health>

## MuMu / ADB 要求

确认 ADB 能看到 MuMu：

```powershell
adb devices
```

期望输出类似：

```text
List of devices attached
127.0.0.1:7555    device
```

如果 ADB 不在 `PATH` 中，可以在 `configs/default.yaml` 中配置：

```yaml
adb:
  path: "C:\\Android\\platform-tools\\adb.exe"
```

FGO 包名也在 `configs/default.yaml` 中配置：

```yaml
fgo:
  package_names:
    - "com.bilibili.fatego"
    - "com.aniplex.fategrandorder"
    - "com.aniplex.fategrandorder.en"
```

## 配置

`configs/default.yaml` 会覆盖 `backend/core/config.py` 中的默认值，包括：

- 服务监听地址和 LAN 设置
- ADB 路径和超时
- 基准分辨率和动作延迟
- 截图间隔
- OpenCV 识别阈值
- 日志设置
- FGO 包名列表

运行时也可以通过 `PATCH /api/settings` 修改部分配置。

## 模板与界面识别

状态识别会从下面目录读取模板图片：

```text
assets/templates/<group>/<name>.png
```

示例：

```text
assets/templates/battle/attack_button.png
assets/templates/support/select_title.png
assets/templates/quest/start_button.png
```

当前模板图片还没有内置，需要从 MuMu 中按固定分辨率截取。当前基准分辨率是 `1280x720`。

如果模板缺失，状态识别可能返回 `UNKNOWN`。一键启动会安全失败并提示 `UNSUPPORTED_START_STATE`，不会盲目点击。

## 坐标

坐标以 `1280x720` 为基准，并集中维护在：

```text
worker/fgo/coordinates.py
```

不要把裸坐标散落在业务逻辑中。后续应增加截图点击式校准界面，让用户在截图上点按钮位置，而不是手动填写坐标数字。

## 测试

运行后端和 Worker 测试：

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
```

运行前端构建：

```powershell
cd frontend
npm run build
```

当前测试覆盖：

- 坐标缩放
- ADB 命令构造和前台包名解析
- 战斗方案解析
- 选卡策略
- 图像识别匹配
- 任务状态转换
- FastAPI CRUD
- WebSocket 事件格式
- 一键启动无设备错误
- 合成截图驱动的 Worker E2E 流程

## 当前 MVP 状态

已实现：

- 实例管理、ADB 扫描、连接测试、截图
- 关卡 / 助战 / 战斗方案配置
- 任务创建、启动、暂停、恢复、停止
- 单实例从当前关卡开始执行
- 助战职介筛选和推荐第一个兜底
- 固定动作战斗执行器，支持宝具顺序和补卡兜底
- AP 不足识别和恢复流程入口
- 异常截图
- WebSocket 实时状态
- React Dashboard、编辑器、运行监控、日志、设置页
- 一键启动预检和任务启动

后续计划：

- 指定好友助战的头像 / 礼装模板识别
- OCR 好友名识别
- 自动日常本导航
- 多实例并发强化
- 卡色识别和智能补卡
- 战斗方案导入导出
- 模板诊断和坐标校准界面
- .NET 8 WebView2 Windows 桌面壳和安装包
- 局域网远程访问和鉴权
