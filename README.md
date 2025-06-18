# Maibot 示例插件：控制台适配器

这是一个功能完整、结构清晰的示例插件，演示了如何使用 `maim_message` 库创建一个与 MaimCore 服务进行交互的控制台适配器。

它包含了配置解耦、日志系统、命令行参数、异步交互优化和面向对象设计等多个良好实践，可作为开发其他 MaimBot 适配器的优秀模板。

## 功能

*   **配置解耦**: 通过 `config.toml` 文件管理所有配置项，无需修改代码。
*   **连接到 MaimCore**: 作为客户端连接到指定的 MaimCore WebSocket 服务，并提供清晰的连接状态反馈。
*   **发送消息**: 从控制台读取用户输入，将其封装成标准的 `MessageBase` 格式，并发送给 MaimCore。
*   **接收消息**: 接收 MaimCore 回复的 `MessageBase` 消息，并将其内容友好地打印到控制台。
*   **日志系统**: 内置 `loguru` 提供美观的日志，并支持通过 `--debug` 开关查看详细的数据流。

## 如何使用

### 1. 安装依赖

确保你已经安装了 Python 3.9+。然后运行以下命令安装所需的库：

```bash
pip install -r requirements.txt
```

### 2. 创建并配置 `config.toml`

本适配器通过 `config.toml` 文件进行配置。请在 `console_adapter.py` 相同目录下创建一个名为 `config.toml` 的文件。

你只需要填入你想自定义的配置项。**任何未在文件中配置的项，程序都会自动使用合理的默认值。**

**`config.toml` 示例:**
```toml
[config]
# [必需] 你的 MaimCore WebSocket 服务地址
MAIMCORE_URL = "ws://127.0.0.1:8000/ws"

# 自定义的适配器平台名称，会显示在 MaimCore 的日志中
PLATFORM_NAME = "my_console"

# 模拟的用户和群组信息
CONSOLE_USER_ID = "user_123"
CONSOLE_NICKNAME = "MyNickname"
# 如果想模拟私聊，可以注释掉下面两行或将其留空
CONSOLE_GROUP_ID = "group_456"
CONSOLE_GROUP_NAME = "My Test Group"
```

> **提示**: 如果你跳过这一步直接运行脚本，程序会提示 `config.toml` 未找到，并全部使用默认值运行。

### 3. 运行适配器

配置完成后，运行脚本：

**普通模式:**
```bash
python console_adapter.py
```

**Debug 模式 (显示详细的收发数据包):**
```bash
python console_adapter.py --debug
```

程序启动后，会尝试连接到 MaimCore。连接成功后，你就可以在控制台输入消息并按回车发送了。

### 4. 退出

在控制台输入 `exit` 或 `quit`，或者按下 `Ctrl+C` 来优雅地退出程序。 