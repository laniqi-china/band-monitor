# tests/unit/test_archive_manager.py
import pytest
import zipfile
import tarfile
import json
from pathlib import Path
import tempfile
import shutil
from datetime import datetime, timedelta

from src.archive_manager import ArchiveManager, ArchiveInfo


class TestArchiveInfo:
    """测试存档信息类"""

    def test_initialization(self, temp_dir):
        """测试初始化"""
        archive_path = temp_dir / "test.zip"

        info = ArchiveInfo(
            path=archive_path,
            format="zip",
            size=1024,
            created=datetime.now(),
            contents=["file1.txt", "file2.txt"],
            metadata={"files_count": 2, "compression_ratio": 50.5},
        )

        assert info.path == archive_path
        assert info.format == "zip"
        assert info.size == 1024
        assert len(info.contents) == 2
        assert info.metadata["files_count"] == 2
        assert info.metadata["compression_ratio"] == 50.5


class TestArchiveManager:
    """测试存档管理器"""

    @pytest.fixture
    def archive_manager(self, temp_dir):
        """创建存档管理器实例"""
        archive_dir = temp_dir / "archive"
        return ArchiveManager(archive_dir, keep_original=False)

    @pytest.fixture
    def sample_files(self, temp_dir):
        """创建示例文件"""
        files = []
        test_dir = temp_dir / "test_files"
        test_dir.mkdir()

        for i in range(3):
            file_path = test_dir / f"test_{i}.txt"
            file_path.write_text(f"测试内容 {i}" * 100)  # 创建足够大的文件
            files.append(file_path)

        return files

    def test_initialization(self, temp_dir):
        """测试初始化"""
        archive_dir = temp_dir / "archive"
        manager = ArchiveManager(archive_dir, keep_original=True)

        assert manager.archive_dir == archive_dir
        assert manager.keep_original is True
        assert archive_dir.exists()  # 目录应该已创建

    def test_archive_logs_zip(self, archive_manager, sample_files):
        """测试ZIP格式存档日志"""
        from datetime import date

        archive_date = date(2024, 1, 1)
        archive_path = archive_manager.archive_logs(
            archive_date, sample_files, format="zip"
        )

        # 验证存档已创建
        assert archive_path is not None
        assert archive_path.exists()
        assert archive_path.suffix == ".zip"

        # 验证存档大小
        assert archive_path.stat().st_size > 0

        # 验证元数据文件
        metadata_file = archive_manager.archive_dir / "metadata_20240101.json"
        assert metadata_file.exists()

        # 验证元数据内容
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        assert metadata["archive_format"] == "zip"
        assert metadata["original_files"] is not None
        assert len(metadata["original_files"]) == 3

        # 验证原始文件已被删除
        for file_path in sample_files:
            assert not file_path.exists()  # keep_original=False

    def test_archive_logs_tar_gz(self, archive_manager, sample_files):
        """测试tar.gz格式存档日志"""
        from datetime import date

        archive_date = date(2024, 1, 1)
        archive_path = archive_manager.archive_logs(
            archive_date, sample_files, format="tar.gz"
        )

        # 验证存档已创建
        assert archive_path is not None
        assert archive_path.exists()
        assert archive_path.suffix == ".gz"

        # 验证存档可以打开
        with tarfile.open(archive_path, "r:gz") as tar:
            members = tar.getmembers()
            assert len(members) == 3

    def test_archive_logs_keep_original(self, temp_dir, sample_files):
        """测试保留原始文件的存档"""
        from datetime import date

        manager = ArchiveManager(temp_dir / "archive", keep_original=True)
        archive_date = date(2024, 1, 1)

        archive_path = manager.archive_logs(archive_date, sample_files, format="zip")

        # 验证存档已创建
        assert archive_path.exists()

        # 验证原始文件仍然存在
        for file_path in sample_files:
            assert file_path.exists()

    def test_archive_logs_empty(self, archive_manager):
        """测试空文件列表存档"""
        from datetime import date

        archive_date = date(2024, 1, 1)
        archive_path = archive_manager.archive_logs(archive_date, [], format="zip")

        # 应该返回None
        assert archive_path is None

    def test_archive_logs_invalid_format(self, archive_manager, sample_files):
        """测试无效格式存档"""
        from datetime import date

        archive_date = date(2024, 1, 1)

        with pytest.raises(ValueError):
            archive_manager.archive_logs(archive_date, sample_files, format="invalid")

    def test_create_zip_archive(self, archive_manager, sample_files, temp_dir):
        """测试创建ZIP存档"""
        archive_path = temp_dir / "test.zip"

        archive_manager._create_zip_archive(archive_path, sample_files)

        # 验证ZIP文件
        assert archive_path.exists()

        # 验证ZIP内容
        with zipfile.ZipFile(archive_path, "r") as zipf:
            # 应该包含所有文件
            assert len(zipf.namelist()) == 3

            # 验证文件名
            for file_path in sample_files:
                assert file_path.name in zipf.namelist()

            # 验证文件内容
            for file_path in sample_files:
                with zipf.open(file_path.name) as zipped_file:
                    content = zipped_file.read().decode("utf-8")
                    assert f"测试内容 {file_path.stem[-1]}" in content

    def test_create_tar_gz_archive(self, archive_manager, sample_files, temp_dir):
        """测试创建tar.gz存档"""
        archive_path = temp_dir / "test.tar.gz"

        archive_manager._create_tar_gz_archive(archive_path, sample_files)

        # 验证tar.gz文件
        assert archive_path.exists()

        # 验证tar.gz内容
        with tarfile.open(archive_path, "r:gz") as tar:
            # 应该包含所有文件
            members = tar.getmembers()
            assert len(members) == 3

            # 验证文件名
            member_names = [member.name for member in members]
            for file_path in sample_files:
                assert file_path.name in member_names

    def test_create_archive_metadata(self, archive_manager, sample_files, temp_dir):
        """测试创建存档元数据"""
        archive_path = temp_dir / "test.zip"
        archive_path.touch()  # 创建空文件

        metadata = archive_manager._create_archive_metadata(archive_path, sample_files)

        # 验证元数据结构
        assert "archive_path" in metadata
        assert "archive_size" in metadata
        assert "archive_format" in metadata
        assert "creation_time" in metadata
        assert "original_files" in metadata
        assert "total_original_size" in metadata
        assert "compression_ratio" in metadata

        # 验证原始文件信息
        assert len(metadata["original_files"]) == 3

        for file_info in metadata["original_files"]:
            assert "path" in file_info
            assert "name" in file_info
            assert "size" in file_info
            assert "exists" in file_info

        # 验证总大小计算
        total_size = sum(file_path.stat().st_size for file_path in sample_files)
        assert metadata["total_original_size"] == total_size

        # 验证压缩比计算（空存档）
        assert metadata["compression_ratio"] == 100.0  # 0字节存档

    def test_calculate_compression_ratio(self, archive_manager, temp_dir):
        """测试计算压缩比"""
        # 创建原始文件
        original_file = temp_dir / "original.txt"
        original_content = "测试内容" * 1000
        original_file.write_text(original_content)
        original_size = original_file.stat().st_size

        # 创建存档文件（模拟压缩）
        archive_file = temp_dir / "archive.zip"
        archive_content = "压缩内容"  # 比原始文件小
        archive_file.write_text(archive_content)
        archive_size = archive_file.stat().st_size

        ratio = archive_manager._calculate_compression_ratio(
            archive_file, [original_file]
        )

        # 验证压缩比计算
        expected_ratio = (1 - archive_size / original_size) * 100
        assert abs(ratio - expected_ratio) < 0.01

    def test_calculate_compression_ratio_zero_original(self, archive_manager, temp_dir):
        """测试原始大小为0的压缩比计算"""
        # 创建空原始文件
        empty_file = temp_dir / "empty.txt"
        empty_file.touch()

        # 创建存档文件
        archive_file = temp_dir / "archive.zip"
        archive_file.write_text("内容")

        ratio = archive_manager._calculate_compression_ratio(archive_file, [empty_file])

        # 应该返回0
        assert ratio == 0.0

    def test_cleanup_original_files(self, archive_manager, sample_files):
        """测试清理原始文件"""
        # 确保文件存在
        for file_path in sample_files:
            assert file_path.exists()

        # 清理文件
        archive_manager._cleanup_original_files(sample_files)

        # 验证文件已被删除
        for file_path in sample_files:
            assert not file_path.exists()

    def test_cleanup_original_files_missing(self, archive_manager, temp_dir):
        """测试清理不存在的原始文件"""
        missing_file = temp_dir / "missing.txt"

        # 应该不抛出异常
        archive_manager._cleanup_original_files([missing_file])

    def test_cleanup_old_archives(self, archive_manager):
        """测试清理旧存档"""
        from datetime import datetime, timedelta

        archive_dir = archive_manager.archive_dir

        # 创建不同时间的存档文件
        old_time = datetime.now() - timedelta(days=35)  # 35天前
        recent_time = datetime.now() - timedelta(days=5)  # 5天前

        # 旧存档
        old_archive = archive_dir / "old_archive.zip"
        old_archive.touch()
        os.utime(old_archive, (old_time.timestamp(), old_time.timestamp()))

        # 新存档
        new_archive = archive_dir / "new_archive.zip"
        new_archive.touch()
        os.utime(new_archive, (recent_time.timestamp(), recent_time.timestamp()))

        # 清理旧存档（保留30天）
        deleted = archive_manager.cleanup_old_archives(retention_days=30)

        # 验证清理结果
        assert len(deleted) == 1
        assert deleted[0] == old_archive

        # 验证文件状态
        assert not old_archive.exists()
        assert new_archive.exists()

    def test_extract_archive_zip(self, archive_manager, temp_dir, sample_files):
        """测试解压ZIP存档"""
        # 先创建ZIP存档
        archive_path = temp_dir / "test.zip"
        with zipfile.ZipFile(archive_path, "w") as zipf:
            for file_path in sample_files:
                zipf.write(file_path, file_path.name)

        # 解压存档
        extracted_files = archive_manager.extract_archive(
            archive_path, temp_dir / "extracted"
        )

        # 验证解压结果
        assert len(extracted_files) == 3

        # 验证提取的文件
        for extracted_file in extracted_files:
            assert extracted_file.exists()
            assert extracted_file.stat().st_size > 0

    def test_extract_archive_tar_gz(self, archive_manager, temp_dir, sample_files):
        """测试解压tar.gz存档"""
        # 先创建tar.gz存档
        archive_path = temp_dir / "test.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            for file_path in sample_files:
                tar.add(file_path, arcname=file_path.name)

        # 解压存档
        extracted_files = archive_manager.extract_archive(
            archive_path, temp_dir / "extracted"
        )

        # 验证解压结果
        assert len(extracted_files) == 3

    def test_extract_archive_invalid(self, archive_manager, temp_dir):
        """测试解压无效存档"""
        # 创建无效存档文件
        invalid_archive = temp_dir / "invalid.txt"
        invalid_archive.write_text("不是存档文件")

        extracted_files = archive_manager.extract_archive(invalid_archive)

        # 应该返回空列表
        assert extracted_files == []

    def test_list_archives(self, archive_manager):
        """测试列出存档"""
        archive_dir = archive_manager.archive_dir

        # 创建不同类型的存档
        archives = [
            archive_dir / "test1.zip",
            archive_dir / "test2.tar.gz",
            archive_dir / "test3.tgz",
            archive_dir / "test4.txt",  # 不是存档文件
        ]

        for archive_path in archives:
            archive_path.touch()

        # 列出存档
        archive_list = archive_manager.list_archives()

        # 应该只返回3个存档文件（排除.txt）
        assert len(archive_list) == 3

        # 验证存档信息
        for archive_info in archive_list:
            assert isinstance(archive_info, ArchiveInfo)
            assert archive_info.path.exists()
            assert archive_info.format in ["zip", "tar.gz"]
            assert archive_info.size == 0  # 空文件

    def test_get_archive_info_zip(self, archive_manager, temp_dir, sample_files):
        """测试获取ZIP存档信息"""
        # 创建ZIP存档
        archive_path = temp_dir / "test.zip"
        with zipfile.ZipFile(archive_path, "w") as zipf:
            for file_path in sample_files:
                zipf.write(file_path, file_path.name)

        info = archive_manager._get_archive_info(archive_path)

        # 验证存档信息
        assert info.path == archive_path
        assert info.format == "zip"
        assert info.size == archive_path.stat().st_size
        assert len(info.contents) == 3
        assert info.metadata["files_count"] == 3

    def test_get_archive_info_tar_gz(self, archive_manager, temp_dir, sample_files):
        """测试获取tar.gz存档信息"""
        # 创建tar.gz存档
        archive_path = temp_dir / "test.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            for file_path in sample_files:
                tar.add(file_path, arcname=file_path.name)

        info = archive_manager._get_archive_info(archive_path)

        # 验证存档信息
        assert info.path == archive_path
        assert info.format == "tar.gz"
        assert info.size == archive_path.stat().st_size
        assert len(info.contents) == 3
