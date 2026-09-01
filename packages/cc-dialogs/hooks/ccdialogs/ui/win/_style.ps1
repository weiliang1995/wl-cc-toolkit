# Shared look-and-feel for cc-dialogs toast panels.
#
# IMPORTANT: every .ps1 in this directory must stay pure ASCII.
# Windows PowerShell 5.1 parses BOM-less .ps1 files using the system ANSI
# code page, so any non-ASCII literal here would be mangled. All display
# text arrives through the JSON params file, which is read with an explicit
# -Encoding UTF8, so it survives intact.

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Per-monitor scaling: without this the panel renders blurry on scaled displays.
if (-not ('CcDpi' -as [type])) {
  Add-Type @'
using System;
using System.Runtime.InteropServices;
public class CcDpi {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
'@
}
try { [void][CcDpi]::SetProcessDPIAware() } catch {}

[System.Windows.Forms.Application]::EnableVisualStyles()
[System.Windows.Forms.Application]::SetCompatibleTextRenderingDefault($false)


function Get-CcTheme {
  # Follow the Windows app theme so the panel does not glare at night.
  $light = 1
  try {
    $light = (Get-ItemProperty -Path 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize' -Name 'AppsUseLightTheme' -ErrorAction Stop).AppsUseLightTheme
  } catch {}

  if ($light -eq 0) {
    return @{
      Back      = [System.Drawing.Color]::FromArgb(32, 32, 32)
      Panel     = [System.Drawing.Color]::FromArgb(43, 43, 43)
      Text      = [System.Drawing.Color]::FromArgb(240, 240, 240)
      Muted     = [System.Drawing.Color]::FromArgb(160, 160, 160)
      Border    = [System.Drawing.Color]::FromArgb(65, 65, 65)
      Accent    = [System.Drawing.Color]::FromArgb(64, 132, 214)
      AccentTxt = [System.Drawing.Color]::White
      BtnBack   = [System.Drawing.Color]::FromArgb(58, 58, 58)
      BtnText   = [System.Drawing.Color]::FromArgb(235, 235, 235)
    }
  }
  return @{
    Back      = [System.Drawing.Color]::FromArgb(249, 249, 249)
    Panel     = [System.Drawing.Color]::White
    Text      = [System.Drawing.Color]::FromArgb(28, 28, 28)
    Muted     = [System.Drawing.Color]::FromArgb(105, 105, 105)
    Border    = [System.Drawing.Color]::FromArgb(222, 222, 222)
    Accent    = [System.Drawing.Color]::FromArgb(0, 103, 192)
    AccentTxt = [System.Drawing.Color]::White
    BtnBack   = [System.Drawing.Color]::FromArgb(251, 251, 251)
    BtnText   = [System.Drawing.Color]::FromArgb(28, 28, 28)
  }
}


function Set-CcRoundedCorners {
  param($Form, [int]$Radius = 10)
  try {
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $d    = $Radius * 2
    $w    = $Form.Width
    $h    = $Form.Height
    $path.AddArc(0, 0, $d, $d, 180, 90)
    $path.AddArc($w - $d, 0, $d, $d, 270, 90)
    $path.AddArc($w - $d, $h - $d, $d, $d, 0, 90)
    $path.AddArc(0, $h - $d, $d, $d, 90, 90)
    $path.CloseAllFigures()
    $Form.Region = New-Object System.Drawing.Region $path
  } catch {}
}


function New-CcToastForm {
  # A borderless panel anchored to the bottom-right, above the taskbar.
  param(
    [string]$Title,
    [int]$Width = 460,
    [int]$Height = 260,
    $Theme
  )

  $form                  = New-Object System.Windows.Forms.Form
  $form.Text             = $Title
  $form.FormBorderStyle  = 'None'
  $form.StartPosition    = 'Manual'
  $form.Size             = New-Object System.Drawing.Size($Width, $Height)
  $form.BackColor        = $Theme.Back
  $form.ForeColor        = $Theme.Text
  $form.TopMost          = $true
  $form.ShowInTaskbar    = $false
  $form.Font             = New-Object System.Drawing.Font('Segoe UI', 9.75)

  $wa = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
  $form.Location = New-Object System.Drawing.Point(
    ($wa.Right - $Width - 16), ($wa.Bottom - $Height - 16))

  # Hairline border, since a borderless form has no edge of its own.
  $form.Add_Paint({
    param($s, $e)
    $pen = New-Object System.Drawing.Pen $script:CcTheme.Border
    $e.Graphics.DrawRectangle($pen, 0, 0, $s.Width - 1, $s.Height - 1)
    $pen.Dispose()
  })

  Set-CcRoundedCorners -Form $form -Radius 10
  return $form
}


function New-CcHeader {
  # Small caption row: an accent dot plus the source label.
  param([string]$Text, $Theme, [int]$Width)

  $lbl           = New-Object System.Windows.Forms.Label
  $lbl.Text      = $Text
  $lbl.ForeColor = $Theme.Muted
  $lbl.Font      = New-Object System.Drawing.Font('Segoe UI', 8.25, [System.Drawing.FontStyle]::Bold)
  $lbl.Location  = New-Object System.Drawing.Point(18, 14)
  $lbl.Size      = New-Object System.Drawing.Size(($Width - 36), 16)
  $lbl.BackColor = [System.Drawing.Color]::Transparent
  return $lbl
}


function New-CcButton {
  param(
    [string]$Text,
    [string]$Tag,
    $Theme,
    [switch]$Primary,
    [int]$Width = 96
  )

  $b                          = New-Object System.Windows.Forms.Button
  $b.Text                     = $Text
  $b.Tag                      = $Tag
  $b.Size                     = New-Object System.Drawing.Size($Width, 32)
  $b.FlatStyle                = 'Flat'
  $b.Cursor                   = [System.Windows.Forms.Cursors]::Hand
  $b.Font                     = New-Object System.Drawing.Font('Segoe UI', 9.75)
  $b.FlatAppearance.BorderSize = 1

  if ($Primary) {
    $b.BackColor                      = $Theme.Accent
    $b.ForeColor                      = $Theme.AccentTxt
    $b.FlatAppearance.BorderColor     = $Theme.Accent
  } else {
    $b.BackColor                      = $Theme.BtnBack
    $b.ForeColor                      = $Theme.BtnText
    $b.FlatAppearance.BorderColor     = $Theme.Border
  }
  return $b
}
