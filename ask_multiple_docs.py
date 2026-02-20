"""
多文档搜索脚本 - 基于 PageIndex 的跨文档推理式检索

使用方法:
    1. 首先生成所有文档的树结构:
       python run_pageindex.py --pdf_path docs/doc1.pdf --if-add-node-text yes
       python run_pageindex.py --pdf_path docs/doc2.pdf --if-add-node-text yes
    
    2. 然后运行多文档搜索:
       python ask_multiple_docs.py --docs_dir results --query "你的问题"
"""

import argparse
import json
import asyncio
import os
from pathlib import Path
from pageindex.utils import ChatGPT_API_async


def load_all_trees(docs_dir):
    """加载目录下所有树结构 JSON 文件"""
    docs = []
    docs_path = Path(docs_dir)
    
    for json_file in docs_path.glob("*_structure.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取文档信息
        doc_name = json_file.stem.replace('_structure', '')
        
        # 处理不同的 JSON 格式
        if isinstance(data, dict) and 'structure' in data:
            tree = data['structure']
            doc_description = data.get('doc_description', '')
        elif isinstance(data, list):
            tree = data
            doc_description = ''
        else:
            continue
        
        docs.append({
            'doc_name': doc_name,
            'tree': tree,
            'doc_description': doc_description,
            'json_file': str(json_file)
        })
    
    print(f"📚 已加载 {len(docs)} 个文档")
    return docs


async def generate_doc_description(tree, model='deepseek-chat'):
    """为文档生成描述"""
    # 创建一个简化的树结构（只保留标题和摘要）
    def simplify_tree(nodes):
        result = []
        for node in nodes:
            simplified = {
                'title': node.get('title', ''),
                'summary': node.get('summary', '')
            }
            if 'nodes' in node and node['nodes']:
                simplified['nodes'] = simplify_tree(node['nodes'])
            result.append(simplified)
        return result
    
    simplified = simplify_tree(tree[:5])  # 只使用前几个节点以节省 token
    
    prompt = f"""
You are given a table of contents structure of a document.
Your task is to generate a one-sentence description for the document that makes it easy to distinguish from other documents.

Document tree structure:
{json.dumps(simplified, indent=2, ensure_ascii=False)}

Directly return the description in Chinese, do not include any other text.
"""
    
    response = await ChatGPT_API_async(model=model, prompt=prompt)
    return response.strip()


async def select_documents(query, docs_with_desc, model='deepseek-chat'):
    """使用 LLM 选择相关文档"""
    docs_info = []
    for doc in docs_with_desc:
        docs_info.append({
            'doc_name': doc['doc_name'],
            'doc_description': doc.get('doc_description', '无描述')
        })
    
    prompt = f"""
你是一个文档检索助手。给定用户问题和一组文档描述，请选择可能包含答案的文档。

问题：{query}

文档列表：
{json.dumps(docs_info, indent=2, ensure_ascii=False)}

请按照以下 JSON 格式回复：
{{
    "thinking": "<你的文档选择推理过程>",
    "answer": [<相关文档名称列表>], 例如 ['doc1', 'doc2']，如果没有相关文档则返回 []
}}

直接返回 JSON 结构，不要输出其他内容。
"""
    
    response = await ChatGPT_API_async(model=model, prompt=prompt)
    result = json.loads(response)
    return result


async def search_single_doc(query, tree, doc_name, model='deepseek-chat'):
    """在单个文档中搜索"""
    # 简化树结构用于检索
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
    return json.loads(search_result)


def find_node_by_id(node_id, nodes_list):
    """递归查找节点"""
    for node in nodes_list:
        if isinstance(node, dict):
            if node.get('node_id') == node_id:
                return node
            if 'nodes' in node:
                found = find_node_by_id(node_id, node['nodes'])
                if found:
                    return found
    return None


def get_node_text(node):
    """获取节点文本"""
    if 'text' in node and node['text']:
        return node['text']
    if 'summary' in node and node['summary']:
        return f"【{node.get('title', 'Untitled')}】\n{node['summary']}"
    return node.get('title', '')


async def ask_multiple_docs(query, docs_dir, model='deepseek-chat', max_docs=3):
    """多文档搜索主函数"""
    
    # 步骤 1: 加载所有文档树
    print("\n📂 正在加载文档树...")
    docs = load_all_trees(docs_dir)
    
    if not docs:
        print("❌ 未找到任何文档树结构文件")
        return
    
    # 步骤 2: 为没有描述的文档生成描述
    print("\n📝 正在生成文档描述...")
    for doc in docs:
        if not doc.get('doc_description'):
            print(f"  - 生成 {doc['doc_name']} 的描述...")
            doc['doc_description'] = await generate_doc_description(doc['tree'], model)
    
    # 步骤 3: 选择相关文档
    print("\n🔍 正在选择相关文档...")
    selection_result = await select_documents(query, docs, model)
    print(f"💡 推理过程：{selection_result.get('thinking', 'N/A')}")
    
    selected_doc_names = selection_result.get('answer', [])
    
    if not selected_doc_names:
        print("⚠️ 未找到相关文档")
        return
    
    print(f"📍 选中 {len(selected_doc_names)} 个文档：{', '.join(selected_doc_names)}")
    
    # 步骤 4: 在选中的文档中搜索
    print("\n📖 正在检索文档内容...")
    all_relevant_content = []
    
    for doc in docs:
        if doc['doc_name'] in selected_doc_names:
            print(f"  - 检索 {doc['doc_name']}...")
            search_result = await search_single_doc(query, doc['tree'], doc['doc_name'], model)
            
            # 提取相关内容
            node_list = search_result.get('node_list', [])
            for node_id in node_list:
                node = find_node_by_id(node_id, doc['tree'])
                if node:
                    text = get_node_text(node)
                    if text:
                        all_relevant_content.append({
                            'doc_name': doc['doc_name'],
                            'node_title': node.get('title', 'Untitled'),
                            'text': text
                        })
    
    if not all_relevant_content:
        print("⚠️ 未找到相关内容")
        return
    
    # 步骤 5: 生成综合答案
    print("\n✍️ 正在生成综合答案...")
    
    context_parts = []
    for item in all_relevant_content:
        context_parts.append(
            f"### 来自文档《{item['doc_name']}》的【{item['node_title']}】:\n{item['text'][:500]}..."
        )
    
    relevant_content = "\n\n".join(context_parts)
    
    answer_prompt = f"""
请根据以下检索到的内容回答问题。请综合多个文档的信息，给出完整、准确的答案。

问题：{query}

检索到的内容：
{relevant_content}

请用中文回答，并注明信息来源的文档名称。
"""
    
    answer = await ChatGPT_API_async(model=model, prompt=answer_prompt)
    return answer, all_relevant_content


async def main():
    parser = argparse.ArgumentParser(description='多文档搜索')
    parser.add_argument('--docs_dir', type=str, required=True, 
                        help='包含树结构 JSON 文件的目录')
    parser.add_argument('--query', type=str, required=True, 
                        help='你的问题')
    parser.add_argument('--model', type=str, default='deepseek-chat',
                        help='使用的模型')
    parser.add_argument('--max_docs', type=int, default=3,
                        help='最多选择的文档数')
    args = parser.parse_args()
    
    print(f"❓ 问题：{args.query}\n")
    print("=" * 60)
    
    result = await ask_multiple_docs(args.query, args.docs_dir, args.model, args.max_docs)
    
    if result:
        answer, sources = result
        print("\n" + "=" * 60)
        print(f"\n✅ 答案:\n{answer}")
        print(f"\n📚 参考来源：{len(sources)} 个节点")
        for src in sources:
            print(f"  - 《{src['doc_name']}》: {src['node_title']}")


if __name__ == "__main__":
    asyncio.run(main())
