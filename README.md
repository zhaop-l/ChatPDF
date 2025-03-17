# ChatPDF - 智能PDF对话工具

🤖 一个基于AI的PDF交互工具，支持通过自然语言对话快速提取、查询和分析PDF文档内容。


## 主要功能

- 📄 PDF文档内容解析与向量化
- 💬 自然语言问答交互
- 🔍 关键信息快速定位
- 📝 自动生成文档摘要
- 🌐 支持多语言文档处理

## 技术栈

- **语言**: Python
- **核心库**: 
  - ChatGLM（大模型交互）
  - PymuPDF（PDF解析）
  - BAAI/bge-large-zh-v1.5（embedding）


## 快速开始

### 环境要求
- Python 3.8+
- torch 2.1.0

### 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/zhaop-l/ChatPDF.git
cd ChatPDF
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

### 使用说明

1. 启动服务：
```bash
python server_api.py
```


## 许可证

[MIT License](LICENSE)

---