"""
定期清理回收站脚本
删除超过指定天数的软删除文件
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.crud.subject import get_file, permanent_delete_file
from app.models.subject import SubjectFile


def clean_expired_files(days: int = 3):
    """
    清理超过指定天数的已删除文件
    :param days: 保留天数，默认3天
    """
    db: Session = SessionLocal()

    try:
        # 计算过期时间点
        expire_time = datetime.utcnow() - timedelta(days=days)

        # 查询过期文件
        expired_files = db.query(SubjectFile).filter(
            SubjectFile.is_deleted == True,
            SubjectFile.deleted_at < expire_time
        ).all()

        deleted_count = 0
        for file in expired_files:
            print(f"🗑️ 清理过期文件: {file.original_filename} (删除于 {file.deleted_at})")
            if permanent_delete_file(db, file.id):
                deleted_count += 1

        print(f"✅ 清理完成，共删除 {deleted_count} 个过期文件")

    except Exception as e:
        print(f"❌ 清理失败: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    # 命令行直接运行，清理3天前的文件
    clean_expired_files(3)