#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

"""
日志模块使用示例

这个脚本展示了如何使用logger模块记录不同级别的日志。
可以通过环境变量MOTU_LOG_LEVEL和MOTU_LOG_TO_FILE控制日志行为。

使用方法：
    python log_example.py

环境变量：
    MOTU_LOG_LEVEL: 日志级别 (debug, info, warning, error, critical, none)
    MOTU_LOG_TO_FILE: 是否输出到文件 (true, false)
"""

import os
import time
from dotenv import load_dotenv
from logger import get_logger, configure_from_env

# 加载环境变量
load_dotenv()

def main():
    # 从环境变量配置日志
    logger = configure_from_env()
    
    # 显示当前日志配置
    log_level = os.environ.get('MOTU_LOG_LEVEL', 'info')
    log_to_file = os.environ.get('MOTU_LOG_TO_FILE', 'false').lower() == 'true'
    print(f"当前日志配置: 级别={log_level}, 输出到文件={log_to_file}")
    print("以下是不同级别的日志示例:")
    print("-" * 50)
    
    # 记录不同级别的日志
    logger.debug("这是一条调试日志 (DEBUG)")
    logger.info("这是一条信息日志 (INFO)")
    logger.warning("这是一条警告日志 (WARNING)")
    logger.error("这是一条错误日志 (ERROR)")
    logger.critical("这是一条严重错误日志 (CRITICAL)")
    
    # 演示带有额外信息的日志
    logger.info("处理用户请求", extra={"user_id": 12345, "ip": "192.168.1.1"})
    
    # 演示异常日志
    try:
        result = 10 / 0
    except Exception as e:
        logger.error(f"计算过程中发生错误: {e}", exc_info=True)
    
    # 创建自定义日志记录器
    custom_logger = get_logger(
        name="custom_module",
        level="debug",
        log_to_console=True,
        log_to_file=log_to_file
    )
    
    custom_logger.info("这是来自自定义日志记录器的消息")
    
    # 模拟应用程序运行
    logger.info("应用程序开始运行...")
    for i in range(3):
        logger.debug(f"执行任务 {i+1}")
        time.sleep(0.5)  # 模拟处理时间
        if i == 1:
            logger.warning("任务执行时间较长")
    logger.info("应用程序运行完成")
    
    print("-" * 50)
    print("日志演示完成。")
    if log_to_file:
        print("日志已保存到 logs/app.log 文件中。")

if __name__ == "__main__":
    main()