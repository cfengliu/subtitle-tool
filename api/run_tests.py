#!/usr/bin/env python3
"""
字幕转录API测试运行脚本
使用更好的测试结构和组织
"""

import subprocess
import sys
import os


def run_all_tests():
    """运行所有测试"""
    print("🚀 运行所有测试...")
    return run_pytest_command([])


def run_unit_tests():
    """运行单元测试"""
    print("🔧 运行单元测试...")
    return run_pytest_command(["-m", "unit"])


def run_api_tests():
    """运行API测试"""
    print("🌐 运行API端点测试...")
    return run_pytest_command(["tests/test_api_endpoints.py"])


def run_utils_tests():
    """运行工具函数测试"""
    print("🛠️ 运行工具函数测试...")
    return run_pytest_command(["tests/test_utils.py"])


def run_model_tests():
    """运行模型测试"""
    print("📦 运行模型类测试...")
    return run_pytest_command(["tests/test_models.py"])


def run_convert_tests():
    """运行转换功能测试"""
    print("🎬 运行视频转换测试...")
    return run_pytest_command(["tests/test_convert.py"])


def run_specific_test(test_path):
    """运行特定测试"""
    print(f"🎯 运行特定测试: {test_path}")
    return run_pytest_command([test_path])


def run_pytest_command(args):
    """执行pytest命令"""
    # 确保在正确的目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    cmd = [sys.executable, "-m", "pytest"] + args + ["-v", "--tb=short", "--color=yes"]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("✅ 测试通过！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 测试失败，退出代码: {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
        return False


def show_help():
    """显示帮助信息"""
    print("""
字幕转录API测试运行器

用法:
    python run_tests.py [选项]

选项:
    all, -a, --all          运行所有测试 (默认)
    unit, -u, --unit       运行单元测试
    api, --api              运行API端点测试
    utils, --utils          运行工具函数测试
    models, --models        运行模型类测试
    convert, --convert      运行视频转换测试
    help, -h, --help       显示此帮助信息
    
    <test_path>             运行特定测试文件或测试方法
                           例如: tests/test_utils.py::TestUtilityFunctions::test_format_timestamp_zero

示例:
    python run_tests.py                    # 运行所有测试
    python run_tests.py api                # 运行API测试
    python run_tests.py tests/test_utils.py # 运行工具函数测试文件
    """)


def main():
    """主函数"""
    if len(sys.argv) == 1:
        # 默认运行所有测试
        success = run_all_tests()
    else:
        arg = sys.argv[1].lower()
        
        if arg in ['all', '-a', '--all']:
            success = run_all_tests()
        elif arg in ['unit', '-u', '--unit']:
            success = run_unit_tests()
        elif arg in ['api', '--api']:
            success = run_api_tests()
        elif arg in ['utils', '--utils']:
            success = run_utils_tests()
        elif arg in ['models', '--models']:
            success = run_model_tests()
        elif arg in ['convert', '--convert']:
            success = run_convert_tests()
        elif arg in ['help', '-h', '--help']:
            show_help()
            return
        else:
            # 作为特定测试路径处理
            success = run_specific_test(sys.argv[1])
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 