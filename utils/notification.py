from plyer import notification


def show_notification(title, message):
    """显示 Windows 系统通知弹窗"""
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Food Shelf Life Tracker",
            timeout=10,
        )
        return True
    except Exception as e:
        print(f"通知发送失败: {e}")
        return False