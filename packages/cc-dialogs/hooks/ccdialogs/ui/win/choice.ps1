param([Parameter(Mandatory=$true)][string]$ParamsPath)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$p = Get-Content -LiteralPath $ParamsPath -Raw -Encoding UTF8 | ConvertFrom-Json

$script:picked = @()

$form                 = New-Object System.Windows.Forms.Form
$form.Text            = $p.title
$form.Size            = New-Object System.Drawing.Size(580, 440)
$form.StartPosition   = 'CenterScreen'
$form.TopMost         = $true
$form.FormBorderStyle = 'Sizable'
$form.MaximizeBox     = $false
$form.MinimizeBox     = $false
$script:form          = $form

$label            = New-Object System.Windows.Forms.Label
$label.Text       = [string]$p.prompt
$label.Location   = New-Object System.Drawing.Point(12, 12)
$label.Size       = New-Object System.Drawing.Size(540, 46)
$label.Font       = New-Object System.Drawing.Font('Segoe UI', 10)
$label.Anchor     = 'Top,Left,Right'
$form.Controls.Add($label)

# 多选用 CheckedListBox，单选用 ListBox —— 勾选框本身就说明了可以多选
if ($p.multi) {
  $list = New-Object System.Windows.Forms.CheckedListBox
  $list.CheckOnClick = $true
} else {
  $list = New-Object System.Windows.Forms.ListBox
}
$list.Location = New-Object System.Drawing.Point(12, 64)
$list.Size     = New-Object System.Drawing.Size(540, 280)
$list.Font     = New-Object System.Drawing.Font('Segoe UI', 10)
$list.Anchor   = 'Top,Left,Right,Bottom'
foreach ($o in $p.options) { [void]$list.Items.Add([string]$o) }
if (-not $p.multi -and $list.Items.Count -gt 0) { $list.SelectedIndex = 0 }
$script:list = $list
$form.Controls.Add($list)

$ok          = New-Object System.Windows.Forms.Button
$ok.Text     = '确定'
$ok.Size     = New-Object System.Drawing.Size(120, 32)
$ok.Location = New-Object System.Drawing.Point(432, 356)
$ok.Anchor   = 'Bottom,Right'
$ok.Add_Click({
  if ($p.multi) {
    $script:picked = @($script:list.CheckedItems)
  } elseif ($null -ne $script:list.SelectedItem) {
    $script:picked = @($script:list.SelectedItem)
  }
  $script:form.Close()
})
$form.Controls.Add($ok)

$cancel          = New-Object System.Windows.Forms.Button
$cancel.Text     = '取消'
$cancel.Size     = New-Object System.Drawing.Size(120, 32)
$cancel.Location = New-Object System.Drawing.Point(304, 356)
$cancel.Anchor   = 'Bottom,Right'
$cancel.Add_Click({ $script:picked = @(); $script:form.Close() })
$form.Controls.Add($cancel)

$form.AcceptButton = $ok
$form.CancelButton = $cancel
$form.Add_Shown({ $script:form.Activate(); $script:list.Focus() })
[void]$form.ShowDialog()

@{ picked = @($script:picked) } | ConvertTo-Json -Compress -Depth 3
