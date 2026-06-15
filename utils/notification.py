import subprocess
import shlex


def show_notification(title, message):
    """通过 PowerShell 调用 Windows 原生弹窗通知（无需第三方库）"""
    try:
        ps_script = (
            '[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") | Out-Null; '
            '$n = New-Object System.Windows.Forms.NotifyIcon; '
            '$n.Icon = [System.Drawing.SystemIcons]::Information; '
            f'$n.BalloonTipTitle = {shlex.quote(title)}; '
            f'$n.BalloonTipText = {shlex.quote(message)}; '
            '$n.Visible = $true; '
            '$n.ShowBalloonTip(10000); '
            'Start-Sleep -Seconds 12; '
            '$n.Dispose()'
        )
        subprocess.run(
            ["powershell", "-STA", "-Command", ps_script],
            capture_output=True,
            timeout=15,
        )
        return True
    except Exception as e:
        print(f"通知发送失败: {e}")
        return False