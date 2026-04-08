# Voice 桌面自动化助手

基于 Ollama + Qwen3-VL 的桌面自动化助手，通过屏幕感知和 AI 推理提供智能操作建议。

## 项目架构

```
Voice Assistant/
├── main_controller.py    # 主控制器（事件驱动架构）
├── screenshot.py         # 屏幕捕获模块（mss + Base64）
├── llm_inference.py      # Ollama 客户端（多模态推理）
├── overlay_ui.py         # PyQt6 透明悬浮界面
├── executor.py           # 自动化执行器（PyAutoGUI 封装）
├── audit.py              # 安全审计模块
├── config.ini            # 配置文件
└── requirements.txt      # 依赖清单
```

## 核心特性

### 1. 事件驱动架构
- 主控制器 (`MainController`) 协调四大模块
- 工作线程 (`WorkerThread`) 处理耗时任务
- PyQt6 信号槽机制确保线程安全

### 2. 多模态 AI 推理
- 对接本地 Ollama 服务
- 支持 qwen3-vl:latest 视觉语言模型
- 屏幕截图 → Base64 → API → 结构化建议

### 3. 透明悬浮 UI
- 无边框、半透明、始终置顶
- 鼠标穿透（按钮除外）
- 快捷键：Ctrl+Space 唤醒/分析

### 4. 安全执行
- 安全模式 (Dry-Run)：仅记录不执行
- 权限白名单：限制可操作应用
- 审计日志：完整操作记录

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Ollama

确保 Ollama 服务运行且已拉取模型：

```bash
# 启动 Ollama 服务
ollama serve

# 拉取模型
ollama pull qwen3-vl:latest
```

### 3. 运行助手

```bash
python main_controller.py
```

### 4. 使用方式

1. 按 `Ctrl+Space` 唤醒界面
2. 再次按 `Ctrl+Space` 触发屏幕分析
3. 查看 AI 建议后选择：
   - **接受** (Enter)：确认执行建议操作
   - **拒绝** (Esc)：取消建议
   - **演示** (Space)：高亮显示目标区域

## 模块说明

### main_controller.py
- 事件驱动核心
- 线程管理
- 配置加载
- 模块协调

### screenshot.py
- `ScreenCapturer` 类
- 全屏/区域截图
- Base64 编码输出
- 敏感区域模糊化

### llm_inference.py
- `LLMInference` 类
- Ollama `/api/chat` 接口
- 响应解析（容错处理）
- 单元测试

### overlay_ui.py
- `OverlayUI` 类
- 透明窗口
- 信号定义
- 快捷键绑定

### executor.py
- `ActionExecutor` 类
- 点击/输入/快捷键
- 安全模式
- 操作日志

### audit.py
- `AuditLogger` 类
- `PermissionWhitelist` 类
- 权限检查装饰器
- 日志文件管理

## 配置文件 (config.ini)

```ini
[ollama]
base_url = http://localhost:11434
model = qwen3-vl:latest
timeout = 60

[screen_capture]
blur_enabled = False

[security]
dry_run = True
allowed_apps = chrome,notepad,excel

[ui]
window_opacity = 0.85
dark_mode = True
```

## 开发注意事项

1. **变量命名**：所有代码遵循 PEP8，无多余空格
2. **路径兼容**：使用 `pathlib` 处理跨平台路径
3. **线程安全**：UI 更新必须通过 pyqtSignal
4. **错误处理**：捕获 Ollama 连接失败、超时等异常

## 许可证

MIT License
