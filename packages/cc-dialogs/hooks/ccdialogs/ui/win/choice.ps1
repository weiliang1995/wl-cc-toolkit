param([Parameter(Mandatory=$true)][string]$ParamsPath)

# Pure ASCII only -- see _style.ps1 for why. All display text comes from
# $ParamsPath, which is read as UTF-8 below.

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
. "$PSScriptRoot\_style.ps1"

$p = Get-Content -LiteralPath $ParamsPath -Raw -Encoding UTF8 | ConvertFrom-Json

$script:CcTheme = Get-CcTheme
$theme          = $script:CcTheme
$script:picked  = @()

$options = @($p.options)
$W       = 470

# Grow with the option count, but stay a panel rather than a window.
$rowH    = 26
$listH   = [Math]::Min([Math]::Max(($options.Count * $rowH + 8), 60), 300)
$H       = 118 + $listH + 54

$form        = New-CcToastForm -Title $p.appName -Width $W -Height $H -Theme $theme
$script:form = $form

$form.Controls.Add((New-CcHeader -Text $p.appName -Theme $theme -Width $W))

$prompt           = New-Object System.Windows.Forms.Label
$prompt.Text      = [string]$p.prompt
$prompt.ForeColor = $theme.Text
$prompt.Font      = New-Object System.Drawing.Font('Segoe UI', 11, [System.Drawing.FontStyle]::Bold)
$prompt.Location  = New-Object System.Drawing.Point(18, 34)
$prompt.Size      = New-Object System.Drawing.Size(($W - 36), 48)
$prompt.BackColor = [System.Drawing.Color]::Transparent
$form.Controls.Add($prompt)

# Checkboxes for multi-select say "you may pick several" without a caption.
if ($p.multi) {
  $list              = New-Object System.Windows.Forms.CheckedListBox
  $list.CheckOnClick = $true
} else {
  $list = New-Object System.Windows.Forms.ListBox
}
$list.Location    = New-Object System.Drawing.Point(18, 88)
$list.Size        = New-Object System.Drawing.Size(($W - 36), $listH)
$list.BackColor   = $theme.Panel
$list.ForeColor   = $theme.Text
$list.BorderStyle = 'FixedSingle'
$list.Font        = New-Object System.Drawing.Font('Segoe UI', 10)
$list.ItemHeight  = 22
foreach ($o in $options) { [void]$list.Items.Add([string]$o) }
if (-not $p.multi -and $list.Items.Count -gt 0) { $list.SelectedIndex = 0 }
$script:list = $list
$form.Controls.Add($list)

$y = $H - 46

$ok          = New-CcButton -Text $p.labels.ok -Tag 'ok' -Theme $theme -Primary -Width 104
$ok.Location = New-Object System.Drawing.Point(($W - 122), $y)
$ok.Add_Click({
  if ($p.multi) {
    $script:picked = @($script:list.CheckedItems)
  } elseif ($null -ne $script:list.SelectedItem) {
    $script:picked = @($script:list.SelectedItem)
  }
  $script:form.Close()
})
$form.Controls.Add($ok)

$cancel          = New-CcButton -Text $p.labels.cancel -Tag 'cancel' -Theme $theme -Width 88
$cancel.Location = New-Object System.Drawing.Point(($W - 218), $y)
$cancel.Add_Click({ $script:picked = @(); $script:form.Close() })
$form.Controls.Add($cancel)

$form.AcceptButton = $ok
$form.CancelButton = $cancel
$form.Add_Shown({ $script:form.Activate(); $script:list.Focus() })
[void]$form.ShowDialog()

@{ picked = @($script:picked) } | ConvertTo-Json -Compress -Depth 3
