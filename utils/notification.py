"""
邮件通知模块 - 通过 SMTP 发送提醒（自动识别 QQ邮箱 / 163邮箱）

环境变量配置（部署时设置）：
    MAIL_SENDER     发件邮箱（如 example@qq.com）
    MAIL_PASSWORD   邮箱授权码（非登录密码）
    MAIL_RECIPIENT  收件邮箱
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mail_config.json"
)


def _detect_smtp(email):
    """根据邮箱地址自动识别 SMTP 服务器"""
    domain = email.lower().split("@")[-1] if "@" in email else ""
    if "163" in domain:
        return "smtp.163.com", 465
    elif "126" in domain:
        return "smtp.126.com", 465
    elif "gmail" in domain:
        return "smtp.gmail.com", 465
    elif "outlook" in domain or "hotmail" in domain:
        return "smtp-mail.outlook.com", 587
    else:
        # 默认 QQ/QQ邮箱 及其他
        return "smtp.qq.com", 465


def _get_config():
    """获取邮件配置：优先环境变量，其次本地配置文件"""
    config = {
        "sender": os.environ.get("MAIL_SENDER", ""),
        "password": os.environ.get("MAIL_PASSWORD", ""),
        "recipient": os.environ.get("MAIL_RECIPIENT", ""),
        "server": os.environ.get("SMTP_SERVER", ""),
        "port": int(os.environ.get("SMTP_PORT", "0")),
    }

    # 如果环境变量不全，尝试读取本地配置
    if not config["sender"] or not config["password"]:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    local = json.load(f)
                    for k in ("sender", "password", "recipient", "server", "port"):
                        if local.get(k):
                            config[k] = local[k]
            except Exception:
                pass

    # 自动识别 SMTP 服务器（如果未手动指定）
    if not config["server"] or config["port"] == 0:
        server, port = _detect_smtp(config["sender"])
        if not config["server"]:
            config["server"] = server
        if config["port"] == 0:
            config["port"] = port

    return config


def save_config(sender, password, recipient):
    """保存邮件配置到本地文件"""
    server, port = _detect_smtp(sender)
    config = {
        "sender": sender,
        "password": password,
        "recipient": recipient,
        "server": server,
        "port": port,
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def show_notification(title, message):
    """发送邮件提醒（兼容原接口）"""
    ok, err = send_email(title, message)
    return ok


def send_email(subject, body):
    """发送一封邮件"""
    config = _get_config()
    if not config["sender"] or not config["password"]:
        print("⚠️  邮件未配置，跳过发送。请在页面侧边栏设置邮箱。")
        return False
    if not config["recipient"]:
        print("⚠️  未设置收件邮箱，跳过发送。")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config["sender"]
        msg["To"] = config["recipient"]

        html_part = MIMEText(body, "html", "utf-8")
        msg.attach(html_part)

        with smtplib.SMTP_SSL(config["server"], config["port"]) as server:
            server.login(config["sender"], config["password"])
            server.sendmail(config["sender"], [config["recipient"]], msg.as_string())

        print(f"📧 邮件已发送至 {config['recipient']}")
        return True, "发送成功"
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False, str(e)


def send_daily_summary(items):
    """发送每日汇总邮件"""
    if not items:
        print("✅ 没有需要提醒的商品")
        return False

    today = __import__("datetime").datetime.today().strftime("%Y-%m-%d")

    # 构建 HTML 邮件内容
    rows_html = ""
    for item in items:
        status = "⚠️ 即将过期" if item["expire_date"] >= today else "🚨 已过期"
        rows_html += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #eee;">{item['name']}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;">{item['category']}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;">{item['expire_date']}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;">{status}</td>
        </tr>"""

    html = f"""
    <div style="max-width:600px;margin:0 auto;font-family:Arial,sans-serif;">
        <div style="background:#ff9800;color:white;padding:20px;text-align:center;border-radius:12px 12px 0 0;">
            <h1 style="margin:0;">🥗 食物保质期提醒</h1>
            <p style="margin:8px 0 0 0;opacity:0.9;">{today}</p>
        </div>
        <div style="background:white;padding:20px;border-radius:0 0 12px 12px;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
            <p style="color:#555;font-size:16px;">以下商品需要您关注：</p>
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#f5f5f5;">
                        <th style="padding:10px;text-align:left;">名称</th>
                        <th style="padding:10px;text-align:left;">分类</th>
                        <th style="padding:10px;text-align:left;">到期日</th>
                        <th style="padding:10px;text-align:left;">状态</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            <p style="color:#999;font-size:12px;margin-top:20px;text-align:center;">
                Food Shelf Life Tracker · 自动提醒邮件
            </p>
        </div>
    </div>"""

    ok, _ = send_email("🥗 食物保质期每日提醒", html)
    return ok