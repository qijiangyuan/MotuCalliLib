# 测试目录

此目录包含项目的所有测试代码，用于验证项目功能的正确性。

## 测试文件

- `test_logger.py` - 测试日志记录功能
- `test_logger_config.py` - 测试日志配置功能
- `test_db.py` - 测试数据库连接和基本查询
- `run_tests.py` - 运行所有测试的脚本
- `log_example.py` - 日志模块使用示例

## 运行测试

### 运行所有测试

```bash
python tests/run_tests.py
```

### 运行单个测试文件

```bash
python tests/test_db.py
```

### 运行日志示例

```bash
# 设置环境变量（Windows PowerShell）
$env:MOTU_LOG_LEVEL="debug"
$env:MOTU_LOG_TO_FILE="true"
python tests/log_example.py

# 设置环境变量（Windows CMD）
set MOTU_LOG_LEVEL=debug
set MOTU_LOG_TO_FILE=true
python tests/log_example.py

# 设置环境变量（Linux/Mac）
export MOTU_LOG_LEVEL=debug
export MOTU_LOG_TO_FILE=true
python tests/log_example.py
```

## 添加新测试

1. 创建新的测试文件，命名为 `test_*.py`
2. 导入 `unittest` 模块
3. 创建继承自 `unittest.TestCase` 的测试类
4. 实现测试方法，方法名必须以 `test_` 开头
5. 在文件末尾添加 `if __name__ == '__main__': unittest.main()`

## 测试最佳实践

- 每个测试方法只测试一个功能点
- 使用 `setUp` 和 `tearDown` 方法进行测试前后的准备和清理工作
- 使用断言方法验证测试结果，如 `assertEqual`、`assertTrue` 等
- 使用日志记录测试过程，便于调试
- 测试应该是独立的，不依赖于其他测试的执行结果