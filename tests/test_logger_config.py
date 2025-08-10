#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest
from unittest.mock import patch
import importlib

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入项目模块
from logger import get_logger, configure_from_env, Logger

class TestLoggerConfig(unittest.TestCase):
    """测试日志配置功能"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 确保日志目录存在
        self.log_dir = os.path.join(project_root, 'logs')
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # 重置Logger单例
        Logger._instance = None
        Logger._initialized = False
        
        # 重新导入logger模块以重置全局变量
        import logger
        importlib.reload(logger)
    
    def test_get_logger(self):
        """测试获取日志记录器"""
        # 重置Logger单例
        Logger._instance = None
        Logger._initialized = False
        
        logger = get_logger('test_config')
        self.assertEqual(logger.name, 'test_config')
        
        # 测试默认日志级别
        self.assertEqual(logger.logger.level, 20)  # INFO级别
    
    @patch.dict(os.environ, {"MOTU_LOG_LEVEL": "debug", "MOTU_LOG_TO_FILE": "true"})
    def test_configure_from_env(self):
        """测试从环境变量配置日志"""
        logger = configure_from_env()
        self.assertEqual(logger.logger.level, 10)  # DEBUG级别
        
        # 检查是否有文件处理器
        has_file_handler = False
        for handler in logger.logger.handlers:
            if handler.__class__.__name__ == 'RotatingFileHandler':
                has_file_handler = True
                break
        
        self.assertTrue(has_file_handler, '没有找到文件处理器')
    
    @patch.dict(os.environ, {"MOTU_LOG_LEVEL": "error", "MOTU_LOG_TO_FILE": "false"})
    def test_log_level_error(self):
        """测试ERROR日志级别配置"""
        logger = configure_from_env()
        self.assertEqual(logger.logger.level, 40)  # ERROR级别
        
        # 检查是否没有文件处理器
        has_file_handler = False
        for handler in logger.logger.handlers:
            if handler.__class__.__name__ == 'RotatingFileHandler':
                has_file_handler = True
                break
        
        self.assertFalse(has_file_handler, '不应该有文件处理器')
    
    def test_chinese_logging(self):
        """测试中文日志记录"""
        logger = get_logger('test_chinese', log_to_file=True)
        test_message = "测试中文日志消息"
        logger.info(test_message)
        
        # 检查日志文件是否存在
        log_file = os.path.join(self.log_dir, 'app.log')
        self.assertTrue(os.path.exists(log_file), '日志文件不存在')
        
        # 检查日志文件中是否包含中文消息
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        self.assertIn(test_message, log_content, '日志文件中没有找到中文消息')

if __name__ == '__main__':
    unittest.main()