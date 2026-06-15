"""
后台提醒脚本 - 检查即将过期的商品并发送 Windows 通知
配合 Windows 任务计划程序每日自动运行一次
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import init_db, get_expiring_soon_items, mark_notified
from utils.notification import show_notification


def check_and_notify():
    init_db()
    items = get_expiring_soon_items(days=5)

    if not items:
        print("✅ 没有即将过期的商品")
        return

    for item in items:
        title = "🥛 食物即将过期提醒"
        message = f'"{item["name"]}" ({item["category"]}) 还有 {item["expire_date"]} 到期，记得及时处理哦！'
        show_notification(title, message)
        mark_notified(item["id"])
        print(f"已提醒: {item['name']}")


if __name__ == "__main__":
    check_and_notify()