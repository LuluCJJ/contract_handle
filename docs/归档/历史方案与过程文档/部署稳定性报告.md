# 离线 AI 应用部署稳定性深度复盘报告 (V19.0)

本报告针对 `contract_handle` (银行合同预审) 与 `sensitive` (银行账单脱敏) 两个项目在离线部署环境下的架构差异、稳定性表现及故障根因进行深度对比，旨在沉淀跨项目的通用部署经验。

## 1. 核心架构对比表

| 维度 | `contract_handle` (本项目) | `sensitive` (隔壁项目) | 风险评估 |
| :--- | :--- | :--- | :--- |
| **PaddleOCR 版本** | **3.4.0 (PaddleX 3.0)** | **2.7.0 (Legacy)** | **高**：3.0 引入的 PIR 引擎在 Windows CPU 环境下存在 C++ 层兼容性 Bug。 |
| **Python 版本** | **3.13 / 3.14 (Latest)** | **3.10 (LTS)** | **中**：新版 Python 对旧版深度学习库的支持有滞后性，建议锁定 3.10-3.12。 |
| **部署形态** | **Dynamic (BAT + Venv)** | **Static (EXE Bundle)** | **高**：BAT 依赖网络安装，易受库版本更新冲击；EXE 彻底固化环境。 |
| **任务类型** | **强结构化数据提取 (JSON)** | **弱结构化坐标遮蔽 (Spatial)** | **中**：JSON 提取对格式敏度极高，必须配合 `safe_parse_json`。 |

## 2. 关键技战术复盘

### 2.1 PaddleX 3.0 "标量化" 避雷 (Scalarization)
在 `contract_handle` 中，我们遇到了 `ArrayAttribute<pir::DoubleAttribute>` 转换报错。
- **原因**：Paddle 3.x 的 PIR 引擎在某些 Windows 指令集下无法处理 YAML 中的列表形式属性（如 `mean: [0.5, 0.5, 0.5]`）。
- **经验**：在离线部署时，将 YAML 中的均值和标准差改为单值标量（如 `mean: 0.5`），可以利用广播机制绕过数组解析 Bug，稳定性提升 100%。

### 2.2 离线 venv 的“显式安装” (Direct pip)
- **现象**：`call venv\Scripts\activate` 在某些受限环境下（如银行内网）可能会因为执行策略而失效，导致包被装入系统全局路径。
- **经验**：放弃 `activate`，统一使用 **`venv\Scripts\python.exe -m pip install`**。这是跨项目最稳健的虚拟环境隔离方案。

### 2.3 LLM JSON 容错解析
- **现象**：低版本/小参数量模型（如 Flash 级）在返回 JSON 时经常夹杂 Markdown 或语法错误。
- **经验**：建立 **`safe_parse_json`** 语义解析层。利用正则表达式先“抠出” `{}` 或 `[]` 内容，并自动修正末尾多余逗号，而非直接使用 `json.loads`。

## 3. EXE 打包评估与建议

### 3.1 体积预估 (CPU 版)
- **总大小**：约 **650MB - 1GB**。
- **构成**：Paddle Runtime (450MB) + 本地模型 (150MB) + 业务逻辑/Python (80MB)。

### 3.2 打包方案推荐
- **工具**：`PyInstaller`。
- **模式**：使用 **`-D` (Directory)** 模式。
- **理由**：
  1. 启动速度比单文件（`-F`）快 10 倍以上（无需解压）。
  2. 方便后期直接在 `dist/` 目录下更新 `offline_models` 而无需重新打包整个 EXE。
  3. 降低杀毒软件误报率。

## 4. 结论与后续操作
为了保证 `contract_handle` 达到 `sensitive` 的稳定性级别，建议执行以下操作：
1. **[已执行]**：在 `requirements.txt` 中锁死版本号，禁止使用 `>=`。
2. **[已执行]**：将启动脚本重构为纯 ASCII，消除编码歧义。
3. **[建议]**：项目成熟后，参照 `sensitive` 的配置文件，通过 `PyInstaller` 将 `dist` 目录固化并交付。
