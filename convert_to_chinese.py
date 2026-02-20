"""
将 Unicode 编码的 JSON 文件转换为中文字符
"""
import json
import sys
import os

# 设置控制台输出编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def convert_json_to_chinese(input_path, output_path=None):
    """转换 JSON 文件为中文"""
    if output_path is None:
        output_path = input_path
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] 已转换：{input_path} -> {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python convert_to_chinese.py <json_file> [output_file]")
        print("示例：python convert_to_chinese.py results/Chengdu_structure.json")
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        convert_json_to_chinese(input_file, output_file)
