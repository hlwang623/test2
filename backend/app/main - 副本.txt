import os
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 导入核心模块
from app.core.database import engine, Base
from app.api import auth, subjects, messages, users

# 显式导入模型以确保 Alembic/SQLAlchemy 能识别到它们 (即便这里不直接使用)
from app.models.subject import Subject
from app.models.message import Message

# 导入清理脚本
# 注意：前提是你是在 backend/ 目录下运行 uvicorn，否则这里可能需要调整引用路径
try:
    from cleanup_trash import clean_expired_files
except ImportError:
    # 容错处理：如果在 IDE 中路径识别错误，避免直接崩溃，仅打印警告
    print("⚠️ 警告: 无法导入 cleanup_trash，后台清理任务将不会启动。")
    clean_expired_files = None


# --- 生命周期管理器 (Lifespan) ---
# 替代旧版的 @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ----------------- 启动阶段 (Startup) -----------------
    print("🔄 系统正在初始化...")

    # 1. 确保上传目录结构存在
    # 建议与 config.py 中的 UPLOAD_DIR 保持一致
    upload_dirs = ["uploads", "uploads/subjects"]
    for dir_path in upload_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"📁 已创建缺失目录: {dir_path}")

    # 2. 初始化数据库表结构
    # 在应用启动时创建所有定义的表 (如果表不存在)
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表结构校验/创建完成")

    # 3. 启动后台清理线程
    if clean_expired_files:
        def background_cleanup_wrapper():
            try:
                # 默认清理 7 天前的文件
                clean_expired_files(days=7)
            except Exception as e:
                print(f"❌ 后台清理任务执行失败: {str(e)}")

        # 使用 daemon=True 确保主程序退出时线程也会随之退出
        cleanup_thread = threading.Thread(target=background_cleanup_wrapper, daemon=True)
        cleanup_thread.start()
        print("🚀 已启动后台回收站清理任务")

    # yield 之前的代码会在应用启动前执行
    yield
    # yield 之后的代码会在应用关闭时执行 (Shutdown)

    # ----------------- 关闭阶段 (Shutdown) -----------------
    print("🛑 服务已关闭，资源已释放。")


# --- 初始化 APP ---
app = FastAPI(
    title="ReBook Edu System API",
    version="1.0.0",
    lifespan=lifespan  # 注入生命周期管理器
)

# --- CORS 配置 ---
origins = [
    "http://localhost:5173",  # Vite 本地开发
    "http://127.0.0.1:5173",  # Vite 备用地址
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 静态文件挂载 ---
# 必须确保目录存在，否则 mount 会报错。lifespan 中已经创建了，但为了双重保险，这里保留检查
if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# --- 路由注册 ---
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(subjects.router)  # 建议在 subjects.router 内部定义 prefix="/api/subjects"
app.include_router(messages.router)  # 建议在 messages.router 内部定义 prefix="/api/messages"
app.include_router(users.router)  # users.router 内部已定义 prefix="/api/users"


@app.get("/")
def read_root():
    return {
        "message": "ReBook System is running",
        "docs_url": "http://127.0.0.1:8080/docs",
        "health": "ok"
    }