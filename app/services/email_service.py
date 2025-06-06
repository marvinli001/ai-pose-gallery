"""
邮件服务模块
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.settings = get_settings()
        self.smtp_server = getattr(self.settings, 'smtp_server', None)
        self.smtp_port = getattr(self.settings, 'smtp_port', 587)
        self.smtp_username = getattr(self.settings, 'smtp_username', None)
        self.smtp_password = getattr(self.settings, 'smtp_password', None)
        self.from_email = getattr(self.settings, 'from_email', None)
        self.enabled = all([self.smtp_server, self.smtp_username, self.smtp_password, self.from_email])
        
        if not self.enabled:
            logger.warning("邮件服务未配置，将跳过邮件发送功能")
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        content: str, 
        html_content: Optional[str] = None
    ) -> bool:
        """
        发送邮件
        
        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            content: 邮件文本内容
            html_content: 邮件HTML内容（可选）
            
        Returns:
            bool: 发送是否成功
        """
        if not self.enabled:
            logger.warning(f"邮件服务未启用，跳过发送邮件到 {to_email}")
            return False
        
        try:
            # 创建邮件消息
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # 添加文本内容
            text_part = MIMEText(content, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # 如果有HTML内容，添加HTML部分
            if html_content:
                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)
            
            # 连接SMTP服务器并发送
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # 启用TLS加密
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"邮件发送成功到 {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败到 {to_email}: {str(e)}")
            return False
    
    async def send_password_reset_email(self, to_email: str, username: str, new_password: str) -> bool:
        """发送密码重置邮件"""
        subject = "[AI姿势参考图库] 密码重置通知"
        
        content = f"""
尊敬的 {username}，

您的账户密码已被管理员重置。

新密码: {new_password}

为了您的账户安全，请登录后立即修改密码。

登录地址: {getattr(self.settings, 'frontend_url', 'http://localhost:8000')}/login

---
AI姿势参考图库 管理团队
        """
        
        html_content = f"""
        <html>
        <body>
            <h2>密码重置通知</h2>
            <p>尊敬的 <strong>{username}</strong>，</p>
            <p>您的账户密码已被管理员重置。</p>
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
                <strong>新密码:</strong> <code>{new_password}</code>
            </div>
            <p>为了您的账户安全，请登录后立即修改密码。</p>
            <p><a href="{getattr(self.settings, 'frontend_url', 'http://localhost:8000')}/login" 
                  style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                立即登录
            </a></p>
            <hr>
            <p><small>AI姿势参考图库 管理团队</small></p>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, content, html_content)
    
    async def send_welcome_email(self, to_email: str, username: str, password: str) -> bool:
        """发送欢迎邮件"""
        subject = "[AI姿势参考图库] 欢迎加入"
        
        content = f"""
欢迎加入 AI姿势参考图库！

尊敬的 {username}，

您的账户已创建成功。

登录信息:
- 用户名: {username}
- 密码: {password}

登录地址: {getattr(self.settings, 'frontend_url', 'http://localhost:8000')}/login

请妥善保管您的登录信息，建议登录后立即修改密码。

---
AI姿势参考图库 管理团队
        """
        
        html_content = f"""
        <html>
        <body>
            <h2>欢迎加入 AI姿势参考图库！</h2>
            <p>尊敬的 <strong>{username}</strong>，</p>
            <p>您的账户已创建成功。</p>
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0;">
                <p><strong>登录信息:</strong></p>
                <ul>
                    <li>用户名: <code>{username}</code></li>
                    <li>密码: <code>{password}</code></li>
                </ul>
            </div>
            <p>请妥善保管您的登录信息，建议登录后立即修改密码。</p>
            <p><a href="{getattr(self.settings, 'frontend_url', 'http://localhost:8000')}/login" 
                  style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                立即登录
            </a></p>
            <hr>
            <p><small>AI姿势参考图库 管理团队</small></p>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, content, html_content)
    
    async def send_admin_message(self, to_email: str, username: str, subject: str, message: str, admin_name: str) -> bool:
        """发送管理员消息"""
        full_subject = f"[AI姿势参考图库] {subject}"
        
        content = f"""
尊敬的 {username}，

您收到来自管理员的消息：

{message}

---
此邮件由管理员 {admin_name} 发送
AI姿势参考图库 管理团队
        """
        
        html_content = f"""
        <html>
        <body>
            <h2>管理员消息</h2>
            <p>尊敬的 <strong>{username}</strong>，</p>
            <p>您收到来自管理员的消息：</p>
            <div style="background-color: #f8f9fa; padding: 20px; border-left: 4px solid #17a2b8; margin: 20px 0;">
                {message.replace('\n', '<br>')}
            </div>
            <hr>
            <p><small>此邮件由管理员 <strong>{admin_name}</strong> 发送</small></p>
            <p><small>AI姿势参考图库 管理团队</small></p>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, full_subject, content, html_content)

# 创建全局邮件服务实例
email_service = EmailService()