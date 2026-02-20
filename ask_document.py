"""
对文档提问的脚本 - 基于 PageIndex 的推理式检索

使用方法:
    python ask_document.py --pdf_path results/your_doc_structure.json --query "你的问题"
"""

import argparse
import json
import asyncio
from pageindex.utils import ChatGPT_API_async


def find_node_by_id(node_id, nodes_list):
    """递归查找节点"""
    for node in nodes_list:
        if node.get('node_id') == node_id:
            return node
        if 'nodes' in node:
            found = find_node_by_id(node_id, node['nodes'])
            if found:
                return found
    return None


def get_node_text(node):
    """获取节点文本"""
    # 优先使用 text 字段
    if 'text' in node and node['text']:
        return node['text']
    # 备选：使用 summary 字段
    if 'summary' in node and node['summary']:
        return f"【{node.get('title', 'Untitled')}】\n{node['summary']}"
    return node.get('title', '')


async def ask_document(query, tree, model='deepseek-chat'):
    """对文档提问的主函数"""
    
    # 步骤 1: 树搜索 - 找到相关节点
    print("🔍 正在搜索相关节点...")
    
    # 移除 text 字段以减少 token 消耗
    def remove_text(obj):
        if isinstance(obj, dict):
            return {k: remove_text(v) for k, v in obj.items() if k != 'text'}
        elif isinstance(obj, list):
            return [remove_text(item) for item in obj]
        return obj
    
    tree_without_text = remove_text(tree)
    
    search_prompt = f"""
You are given a question and a tree structure of a document.
Your task is to find all nodes that are likely to contain the answer to the question.

Question: {query}

Document tree structure:
{json.dumps(tree_without_text, indent=2, ensure_ascii=False)}

Please reply in the following JSON format:
{{
    "thinking": "<Your thinking process on which nodes are relevant>",
    "node_list": ["node_id_1", "node_id_2", ...]
}}
Directly return the final JSON structure. Do not output anything else.
"""
    
    search_result = await ChatGPT_API_async(model=model, prompt=search_prompt)
    search_json = json.loads(search_result)
    
    print(f"💡 推理过程：{search_json.get('thinking', 'N/A')}")
    print(f"📍 找到 {len(search_json.get('node_list', []))} 个相关节点")
    
    # 步骤 2: 提取相关内容
    print("\n📖 正在提取相关内容...")
    node_list = search_json.get('node_list', [])
    
    relevant_texts = []
    for node_id in node_list:
        node = find_node_by_id(node_id, tree)
        if node:
            text = get_node_text(node)
            if text:
                relevant_texts.append(f"## {node.get('title', 'Untitled')}\n\n{text}")
                print(f"  - {node.get('title', 'Untitled')} (页码：{node.get('physical_index', 'N/A')})")
    
    relevant_content = "\n\n".join(relevant_texts)
    
    if not relevant_content:
        return "未找到相关内容"
    
    # 步骤 3: 生成答案
    print("\n✍️ 正在生成答案...")
    
    answer_prompt = f"""
Answer the question based on the context:

Question: {query}
Context:
{relevant_content}

Provide a clear, concise answer based only on the context provided. Use the same language as the question.
"""
    
    answer = await ChatGPT_API_async(model=model, prompt=answer_prompt)
    return answer


async def main():
    parser = argparse.ArgumentParser(description='对文档提问')
    parser.add_argument('--tree_path', type=str, required=True, 
                        help='树结构 JSON 文件路径 (由 run_pageindex.py 生成)')
    parser.add_argument('--query', type=str, required=True, 
                        help='你的问题')
    parser.add_argument('--model', type=str, default='deepseek-chat',
                        help='使用的模型')
    args = parser.parse_args()
    
    # 加载树结构
    print(f"📂 加载树结构：{args.tree_path}")
    with open(args.tree_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 处理不同的 JSON 格式
    if isinstance(data, dict) and 'structure' in data:
        tree = data['structure']
        doc_name = data.get('doc_name', 'Unknown')
        print(f"📄 文档名称：{doc_name}")
    elif isinstance(data, list):
        tree = data
    else:
        print("⚠️ 警告：未知的 JSON 格式，尝试直接使用根对象")
        tree = data if isinstance(data, list) else [data]
    
    print(f"📄 文档包含 {len(tree)} 个顶级节点\n")
    print(f"❓ 问题：{args.query}\n")
    print("=" * 60)
    
    # 提问
    answer = await ask_document(args.query, tree, args.model)
    
    print("\n" + "=" * 60)
    print(f"\n✅ 答案:\n{answer}")


if __name__ == "__main__":
    asyncio.run(main())
