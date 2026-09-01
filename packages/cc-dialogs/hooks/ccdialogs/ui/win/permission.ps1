param([Parameter(Mandatory=$true)][string]$ParamsPath)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$p = Get-Content -LiteralPath $ParamsPath -Raw -Encoding UTF8 | ConvertFrom-Json

$script:result = 'cancel'

$form                 = New-Object System.Windows.Forms.Form
$form.Text            = $p.title
$form.Size            = New-Object System.Drawing.Size(640, 400)
$form.StartPosition   = 'CenterScreen'
$form.TopMost         = $true
$form.FormBorderStyle = 'Sizable'
$form.MaximizeBox     = $false
$form.MinimizeBox     = $false
$script:form          = $form

# 只读多行滚动框：长 Bash 命令与大段 diff 无需截断
$box            = New-Object System.Windows.Forms.TextBox
$box.Multiline  = $true
$box.ReadOnly   = $true
$box.ScrollBars = 'Vertical'
$box.WordWrap   = $true
$box.Font       = New-Object System.Drawing.Font('Consolas', 9)
$box.Text       = [string]$p.body
$box.Location   = New-Object System.Drawing.Point(12, 12)
$box.Size       = New-Object System.Drawing.Size(600, 290)
$box.Anchor     = 'Top,Left,Right,Bottom'
$form.Controls.Add($box)

# 用 $this.Tag 传递按钮语义，避免 GetNewClosure 的作用域坑
$onClick = { $script:result = $this.Tag; $script:form.Close() }

$deny          = New-Object System.Windows.Forms.Button
$deny.Text     = '拒绝'
$deny.Tag      = 'deny'
$deny.Size     = New-Object System.Drawing.Size(120, 32)
$deny.Location = New-Object System.Drawing.Point(364, 316)
$deny.Anchor   = 'Bottom,Right'
$deny.Add_Click($onClick)
$form.Controls.Add($deny)

$allow          = New-Object System.Windows.Forms.Button
$allow.Text     = '允许'
$allow.Tag      = 'allow'
$allow.Size     = New-Object System.Drawing.Size(120, 32)
$allow.Location = New-Object System.Drawing.Point(492, 316)
$allow.Anchor   = 'Bottom,Right'
$allow.Add_Click($onClick)
$form.Controls.Add($allow)

if ($p.allowAlways) {
  $always          = New-Object System.Windows.Forms.Button
  $always.Text     = '总是允许'
  $always.Tag      = 'always'
  $always.Size     = New-Object System.Drawing.Size(120, 32)
  $always.Location = New-Object System.Drawing.Point(236, 316)
  $always.Anchor   = 'Bottom,Right'
  $always.Add_Click($onClick)
  $form.Controls.Add($always)
}

$form.AcceptButton = $allow
$form.CancelButton = $deny
$form.Add_Shown({ $script:form.Activate() })
[void]$form.ShowDialog()

@{ result = $script:result } | ConvertTo-Json -Compress
