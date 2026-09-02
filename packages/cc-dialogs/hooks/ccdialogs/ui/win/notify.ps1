param([Parameter(Mandatory=$true)][string]$ParamsPath)

# Pure ASCII only -- see _style.ps1 for why. Display text comes from
# $ParamsPath, which is read as UTF-8 below.

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

# The balloon lives only as long as this process: exit immediately and it
# never renders.
Start-Sleep -Milliseconds 1500
$icon.Visible = $false
$icon.Dispose()

'{}'
