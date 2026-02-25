#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
开发样本数据导入脚本

功能：
1. 自动创建测试用户（如果不存在）
2. 自动创建测试科目（如果不存在）
3. 导入MinerU解析的样本数据到数据库
4. 支持多次运行（幂等性）

使用方法：
    cd backend
    python scripts/seed_dev_samples.py

清理测试数据：
    python scripts/seed_dev_samples.py --clear

作者：ReBook Team
日期：2026-02-09
"""

import sys
import os

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ⚠️ 重要：切换工作目录到 backend 根目录，确保数据库路径正确
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(backend_root)
print(f"📂 工作目录: {os.getcwd()}")

from pathlib import Path
import shutil
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.user import User
from app.models.subject import Subject, SubjectFile, FileStatus
from app.models.message import Message  # 导入Message模型，让SQLAlchemy能够解析User的关系
from app.schemas.subject import SubjectCreate

# ========== 配置区 ==========

# 测试用户配置
TEST_USER = {
    "username": "dev_test",
    "password": "test123456",  # 测试密码
    "email": "dev@test.com"
}

# 测试科目配置
TEST_SUBJECTS = [
    {
        "name": "概率论与数理统计",
        "description": "盛骤、谢式千、潘承毅编著 第五版（开发样本）",
        "sample_folder": "概率论与数理统计"  # dev_samples/ 下的文件夹名
    }
    # 可以在这里添加更多科目配置
]

# 颜色配置
COVER_COLORS = ["blue", "orange", "purple", "green", "pink", "teal"]

# ========== 工具函数 ==========

def print_step(step_num: int, total: int, message: str):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"[{step_num}/{total}] {message}")
    print(f"{'='*60}")


def print_success(message: str):
    """打印成功信息"""
    print(f"✅ {message}")


def print_info(message: str):
    """打印提示信息"""
    print(f"ℹ️  {message}")


def print_error(message: str):
    """打印错误信息"""
    print(f"❌ {message}")


def print_warning(message: str):
    """打印警告信息"""
    print(f"⚠️  {message}")


# ========== 核心功能 ==========

def get_or_create_user(db: Session) -> User:
    """获取或创建测试用户"""
    user = db.query(User).filter(User.username == TEST_USER["username"]).first()

    if user:
        print_info(f"测试用户已存在: {TEST_USER['username']} (ID: {user.id})")
        return user

    # 创建新用户
    hashed_password = get_password_hash(TEST_USER["password"])
    user = User(
        username=TEST_USER["username"],
        email=TEST_USER["email"],
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    print_success(f"创建测试用户: {TEST_USER['username']} (ID: {user.id})")
    print_info(f"   登录账号: {TEST_USER['username']}")
    print_info(f"   登录密码: {TEST_USER['password']}")
    return user


def get_or_create_subject(db: Session, user_id: int, subject_config: dict) -> Subject:
    """获取或创建科目"""
    subject = db.query(Subject).filter(
        Subject.user_id == user_id,
        Subject.name == subject_config["name"]
    ).first()

    if subject:
        print_info(f"科目已存在: {subject_config['name']} (ID: {subject.id})")
        return subject

    # 创建新科目
    import random
    subject = Subject(
        name=subject_config["name"],
        description=subject_config["description"],
        user_id=user_id,
        cover_color=random.choice(COVER_COLORS),
        total_nodes=0,
        learned_nodes=0,
        status="empty"
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)

    print_success(f"创建科目: {subject_config['name']} (ID: {subject.id})")
    return subject


def find_sample_folder(sample_name: str) -> Path:
    """查找样本文件夹"""
    # dev_samples 目录路径
    dev_samples_dir = Path(__file__).parent.parent / "dev_samples"
    sample_path = dev_samples_dir / sample_name

    if not sample_path.exists():
        raise FileNotFoundError(f"样本文件夹不存在: {sample_path}")

    return sample_path


def find_markdown_file(folder: Path) -> Path:
    """在文件夹中查找markdown文件"""
    for md_file in folder.rglob("*.md"):
        if not md_file.name.startswith("README"):
            return md_file
    raise FileNotFoundError(f"未找到markdown文件: {folder}")


def get_file_size(folder: Path) -> int:
    """计算文件夹大小（字节）"""
    total_size = 0
    for file in folder.rglob("*"):
        if file.is_file():
            total_size += file.stat().st_size
    return total_size


def import_sample(db: Session, subject: Subject, sample_config: dict) -> bool:
    """导入单个样本"""
    try:
        # 1. 查找样本文件夹
        print_info(f"正在查找样本: {sample_config['sample_folder']}")
        sample_folder = find_sample_folder(sample_config["sample_folder"])
        print_success(f"找到样本文件夹: {sample_folder}")

        # 2. 查找markdown文件
        md_file = find_markdown_file(sample_folder)
        print_success(f"找到markdown文件: {md_file.name}")

        # 3. 检查是否已经导入过
        existing_file = db.query(SubjectFile).filter(
            SubjectFile.subject_id == subject.id,
            SubjectFile.original_filename == md_file.stem + ".pdf"
        ).first()

        if existing_file:
            print_warning(f"该样本已导入过 (文件ID: {existing_file.id})，跳过")
            return True

        # 4. 创建文件记录
        file_size = get_file_size(sample_folder)
        file_record = SubjectFile(
            subject_id=subject.id,
            file_name=f"{md_file.stem}.pdf",  # 假设原文件是PDF
            original_filename=f"{md_file.stem}.pdf",
            file_path=f"dev_samples/{sample_config['sample_folder']}",  # 虚拟路径
            pdf_path=None,
            file_type="application/pdf",
            file_size=file_size,
            status=FileStatus.PENDING,
            conversion_status='not_needed',
            parse_progress=0.0
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)
        print_success(f"创建文件记录 (ID: {file_record.id})")

        # 5. 复制样本到标准位置
        target_dir = Path(f"uploads/subjects/{subject.id}/parsed/{file_record.id}")

        # 如果目标已存在，先删除
        if target_dir.exists():
            shutil.rmtree(target_dir)
            print_info(f"清理旧数据: {target_dir}")

        # 复制整个文件夹
        shutil.copytree(sample_folder, target_dir)
        print_success(f"复制样本数据到: {target_dir}")

        # 6. 计算相对路径
        md_relative_path = target_dir / md_file.name
        relative_path = os.path.relpath(md_relative_path, os.getcwd()).replace("\\", "/")

        # 7. 更新文件状态
        file_record.status = FileStatus.READY
        file_record.parsed_content_path = relative_path
        file_record.parse_progress = 100.0
        file_record.parsed_at = datetime.now(timezone.utc)
        db.commit()
        print_success(f"更新文件状态为 READY")

        # 8. 更新科目状态
        subject.status = "ready"
        subject.updated_at = datetime.now(timezone.utc)
        db.commit()
        print_success(f"更新科目状态为 ready")

        print_success(f"样本导入完成！")
        print_info(f"   科目ID: {subject.id}")
        print_info(f"   文件ID: {file_record.id}")
        print_info(f"   Markdown路径: {relative_path}")

        return True

    except Exception as e:
        print_error(f"导入失败: {str(e)}")
        db.rollback()
        return False


def seed_samples():
    """主函数：导入所有样本"""
    print("\n" + "="*60)
    print("🌱 ReBook 开发样本数据导入工具")
    print("="*60)

    # 初始化数据库（如果表不存在则创建）
    print("\n🔧 检查数据库...")
    try:
        Base.metadata.create_all(bind=engine)
        print_success("数据库表已就绪")
    except Exception as e:
        print_error(f"数据库初始化失败: {e}")
        return

    db = SessionLocal()

    try:
        # 步骤1: 创建测试用户
        print_step(1, 3, "创建/获取测试用户")
        user = get_or_create_user(db)

        # 步骤2: 导入所有样本
        print_step(2, 3, "导入样本数据")
        success_count = 0

        for idx, subject_config in enumerate(TEST_SUBJECTS, 1):
            print(f"\n--- [{idx}/{len(TEST_SUBJECTS)}] 处理科目: {subject_config['name']} ---")

            # 2.1 创建科目
            subject = get_or_create_subject(db, user.id, subject_config)

            # 2.2 导入样本
            if import_sample(db, subject, subject_config):
                success_count += 1

        # 步骤3: 完成
        print_step(3, 3, "导入完成")
        print_success(f"成功导入 {success_count}/{len(TEST_SUBJECTS)} 个样本")

        print("\n" + "="*60)
        print("🎉 全部完成！")
        print("="*60)
        print("\n📝 快速开始：")
        print(f"   1. 启动后端服务: cd backend && uvicorn app.main:app --reload --port 8080")
        print(f"   2. 启动前端服务: cd frontend && npm run dev")
        print(f"   3. 登录账号: {TEST_USER['username']}")
        print(f"   4. 登录密码: {TEST_USER['password']}")
        print("\n")

    except Exception as e:
        print_error(f"导入过程发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def clear_test_data():
    """清理测试数据"""
    print("\n" + "="*60)
    print("🗑️  清理测试数据")
    print("="*60)

    db = SessionLocal()

    try:
        # 查找测试用户
        user = db.query(User).filter(User.username == TEST_USER["username"]).first()

        if not user:
            print_info("未找到测试用户，无需清理")
            return

        print_info(f"找到测试用户: {TEST_USER['username']} (ID: {user.id})")

        # 删除用户的所有科目（cascade会自动删除文件记录）
        subjects = db.query(Subject).filter(Subject.user_id == user.id).all()
        subject_count = len(subjects)

        for subject in subjects:
            # 删除文件夹
            files = db.query(SubjectFile).filter(SubjectFile.subject_id == subject.id).all()
            for file in files:
                upload_dir = Path(f"uploads/subjects/{subject.id}")
                if upload_dir.exists():
                    shutil.rmtree(upload_dir)
                    print_info(f"删除上传目录: {upload_dir}")

        # 删除用户（会级联删除科目和文件）
        db.delete(user)
        db.commit()

        print_success(f"已删除测试用户和 {subject_count} 个科目")
        print_success("清理完成！")

    except Exception as e:
        print_error(f"清理失败: {str(e)}")
        db.rollback()
    finally:
        db.close()


# ========== 入口点 ==========

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ReBook 开发样本数据管理工具")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="清理测试数据（删除测试用户和所有关联数据）"
    )

    args = parser.parse_args()

    if args.clear:
        # 确认清理操作
        response = input("⚠️  确认要清理所有测试数据吗？(yes/no): ")
        if response.lower() == "yes":
            clear_test_data()
        else:
            print("❌ 取消清理操作")
    else:
        seed_samples()