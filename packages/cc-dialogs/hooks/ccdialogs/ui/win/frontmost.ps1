param([string]$ParamsPath)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 取 HWND 而非 PID：VS Code / Cursor 的多个窗口共用同一个进程，PID 比对
# 必然误判；GetForegroundWindow 拿到的是具体那一个窗口。
Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public class CcFg {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)]
  public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")]
  public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
'@

$h = [CcFg]::GetForegroundWindow()
if ($h -eq [IntPtr]::Zero) { '{}'; exit 0 }

$len = [CcFg]::GetWindowTextLength($h)
$sb  = New-Object System.Text.StringBuilder ($len + 2)
[void][CcFg]::GetWindowText($h, $sb, $sb.Capacity)

$procId = 0
[void][CcFg]::GetWindowThreadProcessId($h, [ref]$procId)
$app = try { (Get-Process -Id $procId -ErrorAction Stop).ProcessName } catch { '' }

@{ app = $app; title = $sb.ToString() } | ConvertTo-Json -Compress
