import asyncio
import time
import sys
import argparse
from pprint import pformat
from loguru import logger
import toml

from maim_message import (
    BaseMessageInfo, UserInfo, GroupInfo, MessageBase, Seg,
    Router, RouteConfig, TargetConfig
)

# --- 参数解析器 & 日志配置 ---
def setup_logger(debug: bool):
    """
    配置 Loguru 日志记录器。

    Args:
        debug (bool): 如果为 True，则设置日志级别为 DEBUG，否则为 INFO。
    """
    logger.remove()  # 移除默认的处理器
    log_level = "DEBUG" if debug else "INFO"
    # 定义一个美观的控制台日志格式
    log_format = (
        "<green>{time:HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
    )
    logger.add(sys.stderr, level=log_level, format=log_format)

class ConsoleAdapter:
    """
    一个封装了所有逻辑的控制台适配器类。
    
    这个类负责:
    - 加载配置
    - 初始化并管理与 MaimCore 的连接 (通过 Router)
    - 处理来自 MaimCore 的下行消息
    - 从控制台读取用户输入并构建上行消息
    - 运行主事件循环
    """

    def __init__(self):
        """初始化适配器，加载配置并设置 Router"""
        self._load_config()
        self._setup_router()
        self._running = False  # 用于控制主循环的运行状态

    def _load_config(self):
        """
        从 config.toml 加载配置。
        如果文件不存在，则使用硬编码的默认值，并打印警告信息。
        """
        try:
            with open("config.toml", "r", encoding="utf-8") as f:
                config_data = toml.load(f)
            config = config_data.get("config", {})
            logger.info("已成功加载 config.toml 文件。")
        except FileNotFoundError:
            logger.warning("未找到 config.toml 文件，将使用默认配置。")
            config = {}

        # 使用 .get() 方法安全地获取配置项，如果缺失则使用默认值
        self.maimcore_url = config.get("MAIMCORE_URL", "ws://127.0.0.1:8000/ws")
        self.platform_name = config.get("PLATFORM_NAME", "console_adapter")
        self.user_id = config.get("CONSOLE_USER_ID", "console_user")
        self.nickname = config.get("CONSOLE_NICKNAME", "ConsoleUser")
        self.group_id = config.get("CONSOLE_GROUP_ID", "1")
        self.group_name = config.get("CONSOLE_GROUP_NAME", "ConsoleGroup")

    def _setup_router(self):
        """根据加载的配置初始化 Router"""
        route_config = RouteConfig(
            route_config={
                self.platform_name: TargetConfig(
                    url=self.maimcore_url,
                    token=None,  # 如果 MaimCore 需要 Token 认证，在这里填写
                )
            }
        )
        # 将配置好的 loguru logger 实例传递给 Router，统一日志风格
        self.router = Router(config=route_config, custom_logger=logger)

    async def _handle_from_maimcore(self, message_dict: dict):
        """
        处理从 MaimCore 返回的下行消息。
        这是一个回调函数，由 Router 在收到消息时调用。
        """
        # 清理当前输入行，防止日志与用户输入交错
        print("\r\033[K", end="")
        
        logger.debug("<--- 收到原始字典数据 ---\n{}", pformat(message_dict))
        
        try:
            # 核心步骤：将收到的字典反序列化为 MessageBase 对象
            message = MessageBase.from_dict(message_dict)
            logger.debug("<--- 解析后的 MessageBase 对象 ---\n{}", pformat(message))

            logger.info("--- 收到 MaimCore 回复 ---")
            
            # 遍历并打印消息段内容
            if message.message_segment and message.message_segment.type == "seglist":
                for seg in message.message_segment.data:
                    logger.info(f"  [{seg.type}]: {seg.data}")
            elif message.message_segment:
                seg = message.message_segment
                logger.info(f"  [{seg.type}]: {seg.data}")
            else:
                logger.warning("收到的消息中没有消息段 (message_segment)。")
        except Exception:
            logger.exception("处理 MaimCore 消息时发生严重错误")
            
        # 在所有日志输出后，重新打印输入提示符
        print("请输入消息 (或 'exit' 退出): ", end="", flush=True)

    def _construct_message_to_maimcore(self, text_content: str) -> MessageBase:
        """
        根据控制台输入构造标准的上行 MessageBase 对象。
        """
        # 构建用户信息
        user_info = UserInfo(
            platform=self.platform_name, user_id=self.user_id, user_nickname=self.nickname
        )
        # 如果配置了 group_id，则构建群组信息
        group_info = GroupInfo(
            platform=self.platform_name, group_id=self.group_id, group_name=self.group_name
        ) if self.group_id else None
        
        # 聚合所有元信息
        message_info = BaseMessageInfo(
            platform=self.platform_name,
            message_id=f"console_msg_{time.time()}", # 使用时间戳生成一个简单的唯一ID
            time=time.time(),
            user_info=user_info,
            group_info=group_info,
        )
        
        # 构建消息内容段
        message_segment = Seg("seglist", [Seg("text", text_content)])
        
        # 最终封装成 MessageBase 对象
        return MessageBase(message_info=message_info, message_segment=message_segment)

    async def _console_input_loop(self):
        """循环读取控制台输入并发送上行消息"""
        loop = asyncio.get_running_loop()
        while self._running:
            try:
                # 在 executor 中运行 input()，避免阻塞事件循环
                message_text = await loop.run_in_executor(None, input, "")
                
                # 在等待输入时，程序可能已经被要求停止
                if not self._running: break
                
                # 处理退出命令
                if message_text.lower() in ['exit', 'quit']:
                    logger.info("用户请求退出...")
                    self._running = False
                    continue  # 退出循环，不再打印提示
                    
                # 发送非空消息
                if message_text.strip():
                    msg_to_send = self._construct_message_to_maimcore(message_text)
                    await self.router.send_message(msg_to_send)
                    logger.info("消息已发送 -> MaimCore")

                # 修复: 无论是否发送成功 (只要不退出), 都重新打印下一次的输入提示
                print("请输入消息 (或 'exit' 退出): ", end="", flush=True)

            except (EOFError, KeyboardInterrupt):
                self._running = False
                break

    async def run(self):
        """
        启动适配器并处理主事件循环。
        这是适配器的主要入口点。
        """
        logger.info("MaimBot 控制台适配器")
        logger.info("使用 -d 或 --debug 参数可启用详细日志")
        logger.info(f"正在尝试连接到 MaimCore: {self.maimcore_url}")

        self._running = True
        # 注册下行消息处理器
        self.router.register_class_handler(self._handle_from_maimcore)
        # 在后台启动 Router 的主任务
        router_task = asyncio.create_task(self.router.run())

        logger.info("正在建立连接...")
        is_connected = False
        # 循环检查连接状态，最多等待10秒
        for _ in range(10):
            client = self.router.clients.get(self.platform_name)
            if client and client.is_connected():
                logger.success("成功连接到 MaimCore！")
                is_connected = True
                break
            await asyncio.sleep(1)

        # 如果10秒后仍未连接，则报错并退出
        if not is_connected:
            logger.error("连接 MaimCore 失败。请检查 URL 或 MaimCore 服务状态。")
            router_task.cancel()
            return

        # 连接成功后，首次打印输入提示
        print("请输入消息 (或 'exit' 退出): ", end="", flush=True)
        # 启动控制台输入循环
        input_task = asyncio.create_task(self._console_input_loop())
        # 等待输入循环结束 (用户输入 exit 或 Ctrl+C)
        await input_task

        logger.info("正在关闭适配器...")
        # 清理并关闭所有正在运行的任务
        if not router_task.done():
            router_task.cancel()
        await asyncio.gather(router_task, return_exceptions=True)
        logger.info("已关闭。")

if __name__ == "__main__":
    # --- 程序入口 ---
    
    # 1. 解析命令行参数
    parser = argparse.ArgumentParser(description="MaimBot Console Adapter")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # 2. 根据参数设置日志记录器
    setup_logger(args.debug)

    # 3. 创建适配器实例
    adapter = ConsoleAdapter()
    
    # 4. 运行适配器的主循环
    try:
        asyncio.run(adapter.run())
    except KeyboardInterrupt:
        # 捕获 Ctrl+C 中断，以更友好的方式退出
        logger.info("\n用户中断。") 