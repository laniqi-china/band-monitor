# tests/unit/test_email_sender.py
import pytest
import smtplib
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from src.email_sender import EmailSender
from src.config_manager import EmailConfig


class TestEmailSender:
    """测试邮件发送器"""

    @pytest.fixture
    def email_config(self):
        """创建邮件配置"""
        return EmailConfig(
            smtp_server="smtp.test.com",
            smtp_port=587,
            use_ssl=False,
            use_tls=True,
            username="test@test.com",
            password="test_password",
            from_addr="sender@test.com",
            to_addrs=["recipient1@test.com", "recipient2@test.com"],
            cc_addrs=["cc@test.com"],
            subject_prefix="测试",
        )

    @pytest.fixture
    def email_sender(self, email_config):
        """创建邮件发送器实例"""
        return EmailSender(email_config)

    @pytest.fixture
    def sample_attachments(self, temp_dir):
        """创建示例附件"""
        attachments = []

        for i in range(2):
            file_path = temp_dir / f"test_{i}.txt"
            file_path.write_text(f"Test content {i}")
            attachments.append(file_path)

        return attachments

    def test_initialization(self, email_config):
        """测试初始化"""
        sender = EmailSender(email_config)

        assert sender.config == email_config
        assert sender.logger is not None

    def test_create_message_basic(self, email_sender):
        """测试创建基本邮件"""
        subject = "测试主题"
        body = "测试正文"
        content_type = "plain"

        msg = email_sender._create_message(subject, body, content_type)

        # 验证邮件头
        assert msg["From"] == "sender@test.com"
        assert msg["To"] == "recipient1@test.com, recipient2@test.com"
        assert msg["Cc"] == "cc@test.com"
        assert msg["Subject"] == "测试 - 测试主题"

        # 验证正文
        assert msg.get_content_type() == "text/plain"
        assert msg.get_payload() == "测试正文"

    def test_create_message_html(self, email_sender):
        """测试创建HTML邮件"""
        subject = "HTML测试"
        body = "<h1>HTML正文</h1>"
        content_type = "html"

        msg = email_sender._create_message(subject, body, content_type)

        assert msg.get_content_type() == "text/html"
        assert "<h1>HTML正文</h1>" in msg.get_payload()

    def test_create_message_with_attachments(self, email_sender, sample_attachments):
        """测试创建带附件的邮件"""
        subject = "带附件测试"
        body = "测试正文"

        msg = email_sender._create_message(
            subject, body, "plain", attachments=sample_attachments
        )

        # 应该是multipart消息
        assert msg.is_multipart()

        # 计算部分数量（1个正文 + N个附件）
        parts = list(msg.walk())
        assert len(parts) == 3  # multipart容器 + 正文 + 2个附件

        # 验证附件
        attachment_filenames = []
        for part in parts:
            if part.get_content_disposition() == "attachment":
                filename = part.get_filename()
                if filename:
                    attachment_filenames.append(filename)

        assert len(attachment_filenames) == 2
        assert "test_0.txt" in attachment_filenames
        assert "test_1.txt" in attachment_filenames

    def test_add_attachments(self, email_sender, sample_attachments):
        """测试添加附件"""
        # 创建基本消息
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart()
        msg.attach(MIMEText("测试正文", "plain"))

        # 添加附件
        email_sender._add_attachments(msg, sample_attachments)

        # 计算附件数量
        attachment_count = 0
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachment_count += 1

        assert attachment_count == 2

    def test_send_email_success(self, email_sender, mock_smtp_server):
        """测试成功发送邮件"""
        subject = "测试邮件"
        body = "测试正文"

        # 模拟成功发送
        success = email_sender.send_email(subject, body, "plain")

        # 验证发送成功
        assert success is True

        # 验证SMTP调用
        mock_smtp_server.assert_called_once()

        # 验证服务器连接
        mock_smtp_server.return_value.starttls.assert_called_once()
        mock_smtp_server.return_value.login.assert_called_once_with(
            "test@test.com", "test_password"
        )
        mock_smtp_server.return_value.send_message.assert_called_once()
        mock_smtp_server.return_value.quit.assert_called_once()

    def test_send_email_with_ssl(self, email_config):
        """测试使用SSL发送邮件"""
        email_config.use_ssl = True
        email_config.use_tls = False

        sender = EmailSender(email_config)

        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_server = Mock()
            mock_smtp_ssl.return_value = mock_server

            success = sender.send_email("测试", "正文")

            # 应该使用SMTP_SSL
            mock_smtp_ssl.assert_called_once_with("smtp.test.com", 587)

            # 不应该调用starttls
            mock_server.starttls.assert_not_called()

    def test_send_email_without_tls(self, email_config):
        """测试不使用TLS发送邮件"""
        email_config.use_tls = False

        sender = EmailSender(email_config)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server

            success = sender.send_email("测试", "正文")

            # 不应该调用starttls
            mock_server.starttls.assert_not_called()

    def test_send_email_failure(self, email_sender):
        """测试发送邮件失败"""
        subject = "测试邮件"
        body = "测试正文"

        # 模拟SMTP异常
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP连接失败")

            success = email_sender.send_email(subject, body, "plain")

            # 应该返回False
            assert success is False

    def test_send_email_auth_failure(self, email_sender):
        """测试认证失败"""
        subject = "测试邮件"
        body = "测试正文"

        # 模拟认证异常
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server
            mock_server.login.side_effect = Exception("认证失败")

            success = email_sender.send_email(subject, body, "plain")

            assert success is False
            mock_server.quit.assert_called_once()  # 应该仍然尝试退出

    def test_send_daily_report(
        self, email_sender, sample_traffic_records, sample_attachments, mock_smtp_server
    ):
        """测试发送每日报告"""
        from datetime import date

        report_date = date(2024, 1, 1)

        success = email_sender.send_daily_report(
            report_date, sample_traffic_records, attachments=sample_attachments
        )

        # 应该成功发送
        assert success is True

        # 验证邮件发送
        mock_smtp_server.return_value.send_message.assert_called_once()

        # 获取发送的消息
        call_args = mock_smtp_server.return_value.send_message.call_args
        sent_msg = call_args[0][0]  # 第一个位置参数

        # 验证邮件主题
        assert "2024-01-01" in sent_msg["Subject"]
        assert "网络流量监控报告" in sent_msg["Subject"]

        # 验证收件人
        assert "recipient1@test.com" in sent_msg["To"]
        assert "recipient2@test.com" in sent_msg["To"]

        # 验证抄送
        assert "cc@test.com" in sent_msg["Cc"]

    def test_generate_report_html(self, email_sender, sample_traffic_records):
        """测试生成报告HTML"""
        from datetime import date

        report_date = date(2024, 1, 1)

        html_content = email_sender._generate_report_html(
            report_date, sample_traffic_records
        )

        # 应该包含基本元素
        assert "<html" in html_content
        assert "<body" in html_content
        assert "2024-01-01" in html_content

        # 应该包含进程信息
        assert "firefox" in html_content.lower()
        assert "chrome" in html_content.lower()

        # 应该包含流量信息
        assert "mb" in html_content.lower()
        assert "流量" in html_content

        # 应该包含表格
        assert "<table" in html_content
        assert "<tr>" in html_content
        assert "<td>" in html_content

    def test_calculate_report_stats(self, email_sender, sample_traffic_records):
        """测试计算报告统计"""
        stats = email_sender._calculate_report_stats(sample_traffic_records)

        # 验证统计字典结构
        assert isinstance(stats, dict)

        # 验证关键统计
        assert "total_records" in stats
        assert stats["total_records"] == 3

        assert "total_upload_mb" in stats
        assert "total_download_mb" in stats
        assert "unique_processes" in stats
        assert "unique_remotes" in stats

        # 验证流量转换（字节到MB）
        total_upload_bytes = 100 + 50 + 200  # 350
        expected_upload_mb = total_upload_bytes / (1024 * 1024)
        assert abs(stats["total_upload_mb"] - expected_upload_mb) < 0.001

    def test_get_top_processes(self, email_sender, sample_traffic_records):
        """测试获取顶级进程"""
        top_processes = email_sender._get_top_processes(sample_traffic_records, top_n=2)

        # 应该返回2个进程
        assert len(top_processes) == 2

        # 应该按总流量排序
        assert top_processes[0]["process_name"] == "chrome"  # 总流量380
        assert top_processes[1]["process_name"] == "firefox"  # 总流量270

        # 验证进程统计
        for process in top_processes:
            assert "process_name" in process
            assert "upload_mb" in process
            assert "download_mb" in process
            assert "total_mb" in process
            assert "connections" in process

    def test_get_top_remotes(self, email_sender, sample_traffic_records):
        """测试获取顶级远程地址"""
        top_remotes = email_sender._get_top_remotes(sample_traffic_records, top_n=2)

        # 应该返回2个远程地址
        assert len(top_remotes) <= 2

        # 验证远程地址统计
        for remote in top_remotes:
            assert "remote_address" in remote
            assert "upload_mb" in remote
            assert "download_mb" in remote
            assert "access_count" in remote
            assert "common_protocol" in remote
