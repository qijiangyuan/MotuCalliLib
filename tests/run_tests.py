#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入项目模块
from logger import get_logger

def run_all_tests():
    """运行所有测试"""
    # 配置日志
    logger = get_logger('test_runner')
    logger.info('开始运行测试...')
    
    # 手动加载测试模块
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # 添加测试模块
    from tests.test_db import TestDatabase
    from tests.test_logger_config import TestLoggerConfig
    
    # 添加测试类
    test_suite.addTest(test_loader.loadTestsFromTestCase(TestDatabase))
    test_suite.addTest(test_loader.loadTestsFromTestCase(TestLoggerConfig))
    
    # 运行测试
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # 输出测试结果
    logger.info(f'测试完成: 运行 {result.testsRun} 个测试')
    if result.wasSuccessful():
        logger.info('所有测试通过!')
        return 0
    else:
        logger.error(f'测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误')
        return 1

if __name__ == '__main__':
    sys.exit(run_all_tests())