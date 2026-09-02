param([string]$ParamsPath)

# Pure ASCII only -- see _style.ps1 for why.

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Identify the window by HWND, not PID: VS Code and Cursor share one process
# across all their windows, so a PID comparison always misfires.
# GetForegroundWindow gives us the specific window instead.
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
