import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-397c4a76a8f844a5ac6075e014cae58a')
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"  # 或 deepseek-coder
DEEPSEEK_TIMEOUT = 30  # 超时时间（秒）
DEEPSEEK_MAX_RETRIES = 2  # 重试次数

# 是否启用 LLM 目录生成
ENABLE_LLM_TOC = os.getenv('ENABLE_LLM_TOC', 'true').lower() == 'true'

# 如果你安装在其他盘，请手动修改引号内的路径。
SOFFICE_PATH = r"D:\soft\LibreOffice\program\soffice.exe"

# 增加一个检查逻辑，方便调试
if not os.path.exists(SOFFICE_PATH):
    # 尝试检查另一个常见的安装位置 (x86)
    POTENTIAL_PATH_X86 = r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
    if os.path.exists(POTENTIAL_PATH_X86):
        SOFFICE_PATH = POTENTIAL_PATH_X86
    else:
        print(f"⚠️ 警告：LibreOffice 路径不存在: {SOFFICE_PATH}")
        print("   请确保已安装 LibreOffice 并更新 config.py 中的 SOFFICE_PATH")

# 超时配置
CONVERSION_TIMEOUT = 60

# 上传目录
UPLOAD_DIR = "uploads/subjects"

# MinerU 服务配置
MINERU_SERVER_URL = os.getenv(
    "MINERU_SERVER_URL",
    "http://127.0.0.1:8000"  # 默认本地隧道地址
)
MINERU_TIMEOUT = int(os.getenv("MINERU_TIMEOUT", "600"))  # 5分钟
MINERU_ENABLED = os.getenv("MINERU_ENABLED", "true").lower() == "true"