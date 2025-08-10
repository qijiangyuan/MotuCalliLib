#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import sqlite3
import unittest

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入项目模块
from logger import get_logger

class TestDatabase(unittest.TestCase):
    """测试数据库连接和基本查询"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.logger = get_logger('test_db')
        self.db_path = os.path.join(project_root, 'data', 'shufadb.db')
        self.logger.info(f'连接数据库: {self.db_path}')
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
    
    def tearDown(self):
        """测试后的清理工作"""
        self.cursor.close()
        self.conn.close()
        self.logger.info('关闭数据库连接')
    
    def test_tables_exist(self):
        """测试数据库表是否存在"""
        self.logger.info('测试数据库表是否存在')
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in self.cursor.fetchall()]
        self.logger.info(f'数据库表: {tables}')
        
        # 检查必要的表是否存在
        required_tables = ['fonts', 'authors', 'books', 'glyphs', 'images']
        for table in required_tables:
            self.assertIn(table, tables, f'表 {table} 不存在')
    
    def test_data_exists(self):
        """测试数据库中是否有数据"""
        self.logger.info('测试数据库中是否有数据')
        tables = ['fonts', 'authors', 'books', 'glyphs', 'images']
        
        for table in tables:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = self.cursor.fetchone()[0]
            self.logger.info(f'表 {table} 中有 {count} 条记录')
            self.assertGreater(count, 0, f'表 {table} 中没有数据')

if __name__ == '__main__':
    unittest.main()