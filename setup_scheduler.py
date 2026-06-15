"""
设置 Windows 任务计划程序 - 每日自动检查食物保质期提醒

请以管理员身份运行此脚本：
    方式1: 右键 PowerShell → 以管理员身份运行 → python setup_scheduler.py
    方式2: 右键 setup_scheduler.py → 使用 Python 打开
"""

import os
import sys
import subprocess
import ctypes


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def setup_task():
    PYTHON_PATH = os.path.abspath(sys.executable)
    REMINDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminder_service.py")
    TASK_NAME = "FoodShelfLifeReminder"

    ps_script = f'''
    $action = New-ScheduledTaskAction -Execute "{PYTHON_PATH}" -Argument "{REMINDER_PATH}"
    $trigger = New-ScheduledTaskTrigger -Daily -At 09:00
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

    Register-ScheduledTask -TaskName "{TASK_NAME}" `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Force

    if ($?) {{
        Write-Host "✅ 每日提醒任务已创建成功！每天 9:00 自动检查并弹窗提醒。" -ForegroundColor Green
        Write-Host "📌 任务名称: {TASK_NAME}" -ForegroundColor Cyan
    }} else {{
        Write-Host "❌ 创建失败，请尝试以管理员身份运行此脚本。" -ForegroundColor Red
    }}
    '''

    result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)


if __name__ == "__main__":
    if not is_admin():
        print("⚠️  请以管理员身份运行此脚本！")
        print("  右键点击 PowerShell → 以管理员身份运行 → 再执行:")
        print(f"  cd {os.path.dirname(os.path.abspath(__file__))}")
        print("  python setup_scheduler.py")
        input("\n按 Enter 键退出...")
        sys.exit(1)

    setup_task()
    input("\n按 Enter 键退出...")