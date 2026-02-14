"""Email sender module for network monitor reports."""

import logging
import smtplib
from datetime import date
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config_manager import EmailConfig
from src.log_parser import TrafficRecord

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件发送器"""

    def __init__(self, config: EmailConfig):
        """初始化邮件发送器

        Args:
            config: 邮件配置
        """
        self.config = config
        self.logger = logger

    def _create_message(
        self,
        subject: str,
        body: str,
        content_type: str = "plain",
        attachments: Optional[List[Path]] = None,
    ):
        """创建邮件消息

        Args:
            subject: 邮件主题
            body: 邮件正文
            content_type: 内容类型 (plain 或 html)
            attachments: 附件列表

        Returns:
            邮件消息对象 (MIMEText 或 MIMEMultipart)
        """
        if not attachments:
            if content_type == "html":
                msg = MIMEText(body, "html", "utf-8")
            else:
                msg = MIMEText(body, "plain", "utf-8")
        else:
            msg = MIMEMultipart()
            if content_type == "html":
                msg.attach(MIMEText(body, "html", "utf-8"))
            else:
                msg.attach(MIMEText(body, "plain", "utf-8"))
            self._add_attachments(msg, attachments)

        msg["From"] = self.config.from_addr
        msg["To"] = ", ".join(self.config.to_addrs)
        if self.config.cc_addrs:
            msg["Cc"] = ", ".join(self.config.cc_addrs)
        msg["Date"] = formatdate(localtime=True)
        msg["Subject"] = f"{self.config.subject_prefix} - {subject}"

        return msg

    def _add_attachments(self, msg: MIMEMultipart, attachments: List[Path]) -> None:
        """添加附件到邮件

        Args:
            msg: 邮件消息
            attachments: 附件路径列表
        """
        for file_path in attachments:
            try:
                with open(file_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())

                from email import encoders

                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{file_path.name}"',
                )
                msg.attach(part)
                self.logger.debug(f"添加附件: {file_path}")
            except Exception as e:
                self.logger.error(f"添加附件失败 {file_path}: {e}")

    def send_email(
        self,
        subject: str,
        body: str,
        content_type: str = "plain",
        attachments: Optional[List[Path]] = None,
    ) -> bool:
        """发送邮件

        Args:
            subject: 邮件主题
            body: 邮件正文
            content_type: 内容类型
            attachments: 附件列表

        Returns:
            发送是否成功
        """
        server = None
        try:
            msg = self._create_message(subject, body, content_type, attachments)

            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(
                    self.config.smtp_server, self.config.smtp_port
                )
            else:
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)

            if self.config.use_tls and not self.config.use_ssl:
                server.starttls()

            server.login(self.config.username, self.config.password)
            server.send_message(msg)
            self.logger.info(f"邮件发送成功: {subject}")
            return True

        except Exception as e:
            self.logger.error(f"邮件发送失败: {e}")
            return False
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass

    def send_daily_report(
        self,
        report_date: date,
        records: List[TrafficRecord],
        attachments: Optional[List[Path]] = None,
    ) -> bool:
        """发送每日报告

        Args:
            report_date: 报告日期
            records: 流量记录列表
            attachments: 附件列表

        Returns:
            发送是否成功
        """
        try:
            subject = f"{report_date.strftime('%Y-%m-%d')} 网络流量监控报告"
            html_content = self._generate_report_html(report_date, records)

            return self.send_email(subject, html_content, "html", attachments)
        except Exception as e:
            self.logger.error(f"发送日报失败: {e}")
            return False

    def _generate_report_html(
        self, report_date: date, records: List[TrafficRecord]
    ) -> str:
        """生成报告 HTML

        Args:
            report_date: 报告日期
            records: 流量记录列表

        Returns:
            HTML 内容
        """
        if not records:
            return f"""
            <html>
            <body>
                <h1>{report_date.strftime('%Y-%m-%d')} 网络流量监控报告</h1>
                <p>当日无流量记录</p>
            </body>
            </html>
            """

        stats = self._calculate_report_stats(records)
        top_processes = self._get_top_processes(records, top_n=5)
        top_remotes = self._get_top_remotes(records, top_n=5)

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .stats {{ background-color: #f9f9f9; padding: 15px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>{report_date.strftime('%Y-%m-%d')} 网络流量监控报告</h1>
            
            <div class="stats">
                <h2>流量统计</h2>
                <p>总记录数: {stats['total_records']}</p>
                <p>总上传: {stats['total_upload_mb']:.2f} MB</p>
                <p>总下载: {stats['total_download_mb']:.2f} MB</p>
                <p>独立进程数: {stats['unique_processes']}</p>
                <p>独立远程地址数: {stats['unique_remotes']}</p>
            </div>
            
            <h2>流量最高的进程 (Top 5)</h2>
            <table>
                <tr>
                    <th>进程名</th>
                    <th>上传 (MB)</th>
                    <th>下载 (MB)</th>
                    <th>总流量 (MB)</th>
                    <th>连接数</th>
                </tr>
        """

        for proc in top_processes:
            html += f"""
                <tr>
                    <td>{proc['process_name']}</td>
                    <td>{proc['upload_mb']:.2f}</td>
                    <td>{proc['download_mb']:.2f}</td>
                    <td>{proc['total_mb']:.2f}</td>
                    <td>{proc['connections']}</td>
                </tr>
            """

        html += """
            </table>
            
            <h2>最常访问的远程地址 (Top 5)</h2>
            <table>
                <tr>
                    <th>远程地址</th>
                    <th>上传 (MB)</th>
                    <th>下载 (MB)</th>
                    <th>访问次数</th>
                    <th>常用协议</th>
                </tr>
        """

        for remote in top_remotes:
            html += f"""
                <tr>
                    <td>{remote['remote_address']}</td>
                    <td>{remote['upload_mb']:.2f}</td>
                    <td>{remote['download_mb']:.2f}</td>
                    <td>{remote['access_count']}</td>
                    <td>{remote['common_protocol']}</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """

        return html

    def _calculate_report_stats(self, records: List[TrafficRecord]) -> Dict[str, Any]:
        """计算报告统计

        Args:
            records: 流量记录列表

        Returns:
            统计字典
        """
        total_upload = sum(r.upload_bps for r in records)
        total_download = sum(r.download_bps for r in records)
        unique_processes = len(set(r.process_name for r in records))
        unique_remotes = len(set(r.remote_address for r in records))

        return {
            "total_records": len(records),
            "total_upload_mb": total_upload / (1024 * 1024),
            "total_download_mb": total_download / (1024 * 1024),
            "unique_processes": unique_processes,
            "unique_remotes": unique_remotes,
        }

    def _get_top_processes(
        self, records: List[TrafficRecord], top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """获取流量最高的进程

        Args:
            records: 流量记录列表
            top_n: 返回前 N 个进程

        Returns:
            进程统计列表
        """
        # 按进程聚合数据
        process_stats: Dict[str, Dict[str, Any]] = {}
        for record in records:
            name = record.process_name
            if name not in process_stats:
                process_stats[name] = {
                    "process_name": name,
                    "upload_bps": 0,
                    "download_bps": 0,
                    "connections": 0,
                }
            process_stats[name]["upload_bps"] += record.upload_bps
            process_stats[name]["download_bps"] += record.download_bps
            process_stats[name]["connections"] += 1

        # 计算总流量并排序
        for stats in process_stats.values():
            stats["upload_mb"] = stats["upload_bps"] / (1024 * 1024)
            stats["download_mb"] = stats["download_bps"] / (1024 * 1024)
            stats["total_mb"] = stats["upload_mb"] + stats["download_mb"]

        sorted_processes = sorted(
            process_stats.values(), key=lambda x: x["total_mb"], reverse=True
        )

        return sorted_processes[:top_n]

    def _get_top_remotes(
        self, records: List[TrafficRecord], top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """获取最常访问的远程地址

        Args:
            records: 流量记录列表
            top_n: 返回前 N 个地址

        Returns:
            远程地址统计列表
        """
        # 按远程地址聚合数据
        remote_stats: Dict[str, Dict[str, Any]] = {}
        for record in records:
            addr = record.remote_address
            if addr not in remote_stats:
                remote_stats[addr] = {
                    "remote_address": addr,
                    "upload_bps": 0,
                    "download_bps": 0,
                    "access_count": 0,
                    "protocols": {},
                }
            remote_stats[addr]["upload_bps"] += record.upload_bps
            remote_stats[addr]["download_bps"] += record.download_bps
            remote_stats[addr]["access_count"] += 1

            # 统计协议
            proto = record.protocol
            remote_stats[addr]["protocols"][proto] = (
                remote_stats[addr]["protocols"].get(proto, 0) + 1
            )

        # 计算流量和最常见协议
        for stats in remote_stats.values():
            stats["upload_mb"] = stats["upload_bps"] / (1024 * 1024)
            stats["download_mb"] = stats["download_bps"] / (1024 * 1024)

            # 找出最常见的协议
            if stats["protocols"]:
                stats["common_protocol"] = max(
                    stats["protocols"], key=stats["protocols"].get
                )
            else:
                stats["common_protocol"] = "unknown"

        sorted_remotes = sorted(
            remote_stats.values(), key=lambda x: x["access_count"], reverse=True
        )

        return sorted_remotes[:top_n]
