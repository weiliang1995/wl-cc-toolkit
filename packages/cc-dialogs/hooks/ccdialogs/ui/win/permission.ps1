param([Parameter(Mandatory=$true)][string]$ParamsPath)

# Pure ASCII only -- see _style.ps1 for why. All display text comes from
# $ParamsPath, which is read as UTF-8 below.

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
. "$PSScriptRoot\_style.ps1"

$p = Get-Content -LiteralPath $ParamsPath -Raw -Encoding UTF8 | ConvertFrom-Json

$script:CcTheme = Get-CcTheme
$theme          = $script:CcTheme
$script:result  = 'cancel'

$W = $theme.Width
$H = 300

$form         = New-CcToastForm -Title $p.appName -Width $W -Height $H -Theme $theme
$script:form  = $form
Add-CcAutoClose -Form $form -Theme $theme

$form.Controls.Add((New-CcHeader -Text $p.appName -Theme $theme -Width $W))

$title           = New-Object System.Windows.Forms.Label
$title.Text      = [string]$p.title
$title.ForeColor = $theme.Text
$title.Font      = New-Object System.Drawing.Font($theme.Font, ($theme.FontSize + 1.25), [System.Drawing.FontStyle]::Bold)
$title.Location  = New-Object System.Drawing.Point(18, 34)
$title.Size      = New-Object System.Drawing.Size(($W - 36), 24)
$title.BackColor = [System.Drawing.Color]::Transparent
$form.Controls.Add($title)

# Scrollable read-only body: long bash commands and big diffs stay legible
# without truncation.
$box              = New-Object System.Windows.Forms.TextBox
$box.Multiline    = $true
$box.ReadOnly     = $true
$box.ScrollBars   = 'Vertical'
$box.WordWrap     = $true
$box.BorderStyle  = 'FixedSingle'
$box.BackColor    = $theme.Panel
$box.ForeColor    = $theme.Text
$box.Font         = New-Object System.Drawing.Font($theme.MonoFont, ($theme.FontSize - 0.25))
$box.Text         = [string]$p.body
$box.Location     = New-Object System.Drawing.Point(18, 66)
$box.Size         = New-Object System.Drawing.Size(($W - 36), 148)
$box.TabStop      = $false
$form.Controls.Add($box)

$onClick = { $script:result = $this.Tag; $script:form.Close() }

$y = $H - 50

$allow          = New-CcButton -Text $p.labels.allow -Tag 'allow' -Theme $theme -Primary -Width 104
$allow.Location = New-Object System.Drawing.Point(($W - 122), $y)
$allow.Add_Click($onClick)
$form.Controls.Add($allow)

$deny           = New-CcButton -Text $p.labels.deny -Tag 'deny' -Theme $theme -Width 88
$deny.Location  = New-Object System.Drawing.Point(($W - 218), $y)
$deny.Add_Click($onClick)
$form.Controls.Add($deny)

if ($p.allowAlways) {
  $always          = New-CcButton -Text $p.labels.always -Tag 'always' -Theme $theme -Width 108
  $always.Location = New-Object System.Drawing.Point(18, $y)
  $always.Add_Click($onClick)
  $form.Controls.Add($always)
}

$form.AcceptButton = $allow
$form.CancelButton = $deny
$form.Add_Shown({ $script:form.Activate(); $allow.Focus() })
[void]$form.ShowDialog()

@{ result = $script:result } | ConvertTo-Json -Compress
