#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库检查工具

这个脚本用于检查书法数据库的结构、数据完整性和统计信息。
可以用于开发调试和数据库维护。

使用方法：
    python tools/check_db.py [选项]

选项：
    --tables: 显示所有表的结构
    --stats: 显示统计信息
    --samples: 显示示例数据
    --all: 显示所有信息（默认）
"""

import sqlite3
import os
import sys
import argparse
from datetime import datetime

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from logger import get_logger

class DatabaseChecker:
    """数据库检查器类"""
    
    def __init__(self, db_path=None):
        """初始化数据库检查器"""
        if db_path is None:
            self.db_path = os.path.join(project_root, 'data', 'shufadb.db')
        else:
            self.db_path = db_path
            
        self.logger = get_logger(
            name="db_checker",
            level="info",
            log_to_console=True,
            log_to_file=False
        )
        
        # 检查数据库文件是否存在
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            self.logger.error(f"连接数据库失败: {e}")
            raise
    
    def get_tables(self):
        """获取所有表名"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            return [row[0] for row in cursor.fetchall()]
    
    def get_table_info(self, table_name):
        """获取表结构信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            return cursor.fetchall()
    
    def get_table_count(self, table_name):
        """获取表记录数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
    
    def get_sample_data(self, table_name, limit=5):
        """获取表的示例数据"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
            return cursor.fetchall()
    
    def check_tables(self):
        """检查所有表的结构"""
        print("=" * 60)
        print("数据库表结构检查")
        print("=" * 60)
        
        tables = self.get_tables()
        print(f"数据库文件: {self.db_path}")
        print(f"发现 {len(tables)} 个表:")
        
        for table in tables:
            print(f"\n📋 表名: {table}")
            print("-" * 40)
            
            # 获取表结构
            columns = self.get_table_info(table)
            print("  列信息:")
            for col in columns:
                pk_mark = " (主键)" if col[5] else ""
                not_null = " NOT NULL" if col[3] else ""
                default = f" DEFAULT {col[4]}" if col[4] else ""
                print(f"    - {col[1]}: {col[2]}{not_null}{default}{pk_mark}")
            
            # 获取记录数
            try:
                count = self.get_table_count(table)
                print(f"  记录数: {count:,}")
            except Exception as e:
                print(f"  记录数: 无法获取 ({e})")
    
    def check_statistics(self):
        """检查数据库统计信息"""
        print("=" * 60)
        print("数据库统计信息")
        print("=" * 60)
        
        tables = self.get_tables()
        total_records = 0
        
        print(f"数据库文件: {self.db_path}")
        file_size = os.path.getsize(self.db_path)
        print(f"文件大小: {file_size:,} 字节 ({file_size/1024/1024:.2f} MB)")
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        print("各表记录统计:")
        for table in tables:
            try:
                count = self.get_table_count(table)
                total_records += count
                print(f"  {table:<15}: {count:>10,} 条记录")
            except Exception as e:
                print(f"  {table:<15}: {'错误':>10} ({e})")
        
        print("-" * 30)
        print(f"  {'总计':<15}: {total_records:>10,} 条记录")
        
        # 检查关键表的数据完整性
        print("\n数据完整性检查:")
        self._check_data_integrity()
    
    def _check_data_integrity(self):
        """检查数据完整性"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查是否有孤立的记录
            checks = [
                {
                    "name": "字形表中的字体ID",
                    "query": """
                        SELECT COUNT(*) FROM glyphs g 
                        LEFT JOIN fonts f ON g.font_id = f.id 
                        WHERE f.id IS NULL
                    """
                },
                {
                    "name": "字形表中的作者ID", 
                    "query": """
                        SELECT COUNT(*) FROM glyphs g 
                        LEFT JOIN authors a ON g.author_id = a.id 
                        WHERE a.id IS NULL
                    """
                },
                {
                    "name": "字形表中的书籍ID",
                    "query": """
                        SELECT COUNT(*) FROM glyphs g 
                        LEFT JOIN books b ON g.book_id = b.id 
                        WHERE b.id IS NULL
                    """
                },
                {
                    "name": "图片表中的字形ID",
                    "query": """
                        SELECT COUNT(*) FROM images i 
                        LEFT JOIN glyphs g ON i.glyph_id = g.id 
                        WHERE g.id IS NULL
                    """
                }
            ]
            
            for check in checks:
                try:
                    cursor.execute(check["query"])
                    count = cursor.fetchone()[0]
                    status = "✓ 正常" if count == 0 else f"✗ 发现 {count} 个问题"
                    print(f"  {check['name']:<20}: {status}")
                except Exception as e:
                    print(f"  {check['name']:<20}: ✗ 检查失败 ({e})")
    
    def show_samples(self):
        """显示示例数据"""
        print("=" * 60)
        print("数据库示例数据")
        print("=" * 60)
        
        tables = self.get_tables()
        
        for table in tables:
            print(f"\n📋 表: {table}")
            print("-" * 40)
            
            try:
                samples = self.get_sample_data(table, 3)
                if samples:
                    # 获取列名
                    columns = self.get_table_info(table)
                    col_names = [col[1] for col in columns]
                    
                    print("  示例记录:")
                    for i, sample in enumerate(samples, 1):
                        print(f"    记录 {i}:")
                        for j, value in enumerate(sample):
                            if j < len(col_names):
                                # 截断过长的值
                                display_value = str(value)
                                if len(display_value) > 50:
                                    display_value = display_value[:47] + "..."
                                print(f"      {col_names[j]}: {display_value}")
                else:
                    print("  无数据")
            except Exception as e:
                print(f"  获取示例数据失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="书法数据库检查工具")
    parser.add_argument("--tables", action="store_true", help="显示表结构")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--samples", action="store_true", help="显示示例数据")
    parser.add_argument("--all", action="store_true", help="显示所有信息")
    parser.add_argument("--db", help="指定数据库文件路径")
    
    args = parser.parse_args()
    
    # 如果没有指定任何选项，默认显示所有信息
    if not any([args.tables, args.stats, args.samples, args.all]):
        args.all = True
    
    try:
        checker = DatabaseChecker(args.db)
        
        if args.all or args.stats:
            checker.check_statistics()
            
        if args.all or args.tables:
            if args.all or args.stats:
                print("\n")
            checker.check_tables()
            
        if args.all or args.samples:
            if args.all or args.stats or args.tables:
                print("\n")
            checker.show_samples()
            
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())