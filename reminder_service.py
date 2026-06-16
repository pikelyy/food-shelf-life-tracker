"""
后台提醒脚本 - 检查即将过期的商品并发送邮件汇总

在 Streamlit Cloud 上通过 GitHub Actions / Cron 定时触发
在本地可直接运行：python reminder_service.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import init_db, get_expiring_soon_items, get_expired_items, mark_notified
from utils.notification import send_daily_summary


def check_and_notify():
    init_db()

    # 获取即将过期（5天内）和已过期的商品
    expiring = get_expiring_soon_items(days=5)
    expired = get_expired_items()
    all_items = expiring + expired

    if not all_items:
        print("✅ 没有需要提醒的商品")
        return

    # 发送汇总邮件
    ok = send_daily_summary(all_items)

    if ok:
        # 标记已通知（仅标记即将过期的，已过期的每次都会提醒）
        for item in expiring:
            mark_notified(item["id"])


if __name__ == "__main__":
    check_and_notify()