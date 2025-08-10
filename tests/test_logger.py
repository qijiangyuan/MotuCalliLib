#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os

# 确保日志目录存在
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_dir = os.path.join(project_root, 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志
logger = logging.getLogger('test')
logger.setLevel(logging.INFO)

# 创建文件处理器
log_file = os.path.join(log_dir, 'test.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# 创建格式化器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# 添加处理器到日志记录器
logger.addHandler(file_handler)

# 记录一些日志
logger.info('这是一条测试日志消息')
logger.warning('这是一条警告消息')

print(f'日志已写入: {log_file}')
print(f'日志文件大小: {os.path.getsize(log_file)} 字节')