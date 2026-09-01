param([Parameter(Mandatory=$true)][string]$ParamsPath)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$p = Get-Content -LiteralPath $ParamsPath -Raw -Encoding UTF8 | ConvertFrom-Json

$icon                 = New-Object System.Windows.Forms.NotifyIcon
$icon.Icon            = [System.Drawing.SystemIcons]::Information
$icon.Visible         = $true
$icon.BalloonTipTitle = [string]$p.title
$icon.BalloonTipText  = [string]$p.body
$icon.ShowBalloonTip(5000)

# NotifyIcon 的气泡依赖进程存活：立即退出气泡就不显示。
Start-Sleep -Milliseconds 1500
$icon.Visible = $false
$icon.Dispose()

'{}'
