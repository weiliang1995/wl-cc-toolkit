# Shared look-and-feel for cc-dialogs panels.
#
# IMPORTANT: every .ps1 in this directory must stay pure ASCII.
# Windows PowerShell 5.1 parses BOM-less .ps1 files using the system ANSI
# code page, so any non-ASCII literal here would be mangled. All display
# text arrives through the JSON params file, which is read with an explicit
# -Encoding UTF8, so it survives intact.
#
# Appearance is overridable without touching this file: see style.json,
# documented in ../../../../STYLE.md.

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

# A panel sets Form.TopMost once and leaves it there. An earlier version also
# re-asserted HWND_TOPMOST on a timer, so that a toast appearing later could
# not cover the buttons -- but among topmost windows Windows fronts whichever
# was raised last, so two panels from two sessions ended up taking turns
# covering each other for as long as both were open. One panel that a toast
# can cover is worth more than two panels that flicker.
try { [void][CcDpi]::SetProcessDPIAware() } catch {}

[System.Windows.Forms.Application]::EnableVisualStyles()
[System.Windows.Forms.Application]::SetCompatibleTextRenderingDefault($false)

# By default WinForms catches exceptions thrown on the UI thread and shows its
# own "Unhandled exception" dialog. That dialog is modal, so it steals focus
# and leaves our panel visible but unclickable -- the worst possible failure.
# Let exceptions propagate instead: the script dies, stdout is empty, and the
# silent-fallback rule takes over and returns the user to the terminal prompt.
try {
  [System.Windows.Forms.Application]::SetUnhandledExceptionMode(
    [System.Windows.Forms.UnhandledExceptionMode]::ThrowException)
} catch {}


function Get-CcStyleConfig {
  # User overrides, if any. Missing file or bad JSON just means defaults.
  $path = Join-Path $env:LOCALAPPDATA 'cc-dialogs\style.json'
  if (-not (Test-Path -LiteralPath $path)) { return $null }
  try {
    return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
  } catch { return $null }
}


function ConvertTo-CcColor {
  param([string]$Hex, $Fallback)
  if ([string]::IsNullOrWhiteSpace($Hex)) { return $Fallback }
  try { return [System.Drawing.ColorTranslator]::FromHtml($Hex) }
  catch { return $Fallback }
}


function Get-CcTheme {
  # Follow the Windows app theme so the panel does not glare at night.
  $cfg = Get-CcStyleConfig

  $mode = $null
  if ($cfg -and $cfg.mode) { $mode = [string]$cfg.mode }

  if (-not $mode -or $mode -eq 'auto') {
    $light = 1
    try {
      $light = (Get-ItemProperty -Path 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize' -Name 'AppsUseLightTheme' -ErrorAction Stop).AppsUseLightTheme
    } catch {}
    $mode = if ($light -eq 0) { 'dark' } else { 'light' }
  }

  if ($mode -eq 'dark') {
    $t = @{
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
  } else {
    $t = @{
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

  # Layout knobs, overridable alongside the colors.
  $t.Font       = 'Segoe UI'
  $t.FontSize   = 9.75
  $t.MonoFont   = 'Consolas'
  $t.Width      = 470
  $t.Radius     = 10
  $t.Corner     = 'bottom-right'
  $t.Margin     = 16
  $t.AutoClose  = 570   # seconds; stay under the 600s hook timeout
  $t.Mode       = $mode

  if ($cfg) {
    $colors = $cfg.$mode
    if ($colors) {
      foreach ($k in @('Back','Panel','Text','Muted','Border','Accent','AccentTxt','BtnBack','BtnText')) {
        $v = $colors.$k
        if ($v) { $t[$k] = ConvertTo-CcColor -Hex ([string]$v) -Fallback $t[$k] }
      }
    }
    if ($cfg.font)      { $t.Font      = [string]$cfg.font }
    if ($cfg.fontSize)  { $t.FontSize  = [double]$cfg.fontSize }
    if ($cfg.monoFont)  { $t.MonoFont  = [string]$cfg.monoFont }
    if ($cfg.width)     { $t.Width     = [int]$cfg.width }
    if ($cfg.corner)    { $t.Corner    = [string]$cfg.corner }
    if ($cfg.margin -ne $null)  { $t.Margin    = [int]$cfg.margin }
    if ($cfg.radius -ne $null)  { $t.Radius    = [int]$cfg.radius }
    if ($cfg.autoCloseSeconds -ne $null) { $t.AutoClose = [int]$cfg.autoCloseSeconds }
  }

  return $t
}


function Set-CcRoundedCorners {
  param($Form, [int]$Radius = 10)
  if ($Radius -le 0) { return }
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
  param(
    [string]$Title,
    [int]$Width = 0,
    [int]$Height = 260,
    $Theme
  )

  if ($Width -le 0) { $Width = $Theme.Width }

  $form                  = New-Object System.Windows.Forms.Form
  $form.Text             = $Title
  $form.FormBorderStyle  = 'None'
  $form.StartPosition    = 'Manual'
  $form.Size             = New-Object System.Drawing.Size($Width, $Height)
  $form.BackColor        = $Theme.Back
  $form.ForeColor        = $Theme.Text
  $form.TopMost          = $true
  $form.ShowInTaskbar    = $false
  $form.Font             = New-Object System.Drawing.Font($Theme.Font, $Theme.FontSize)

  $wa = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
  $m  = $Theme.Margin
  switch ($Theme.Corner) {
    'bottom-left'  { $x = $wa.Left + $m;              $y = $wa.Bottom - $Height - $m }
    'top-right'    { $x = $wa.Right - $Width - $m;    $y = $wa.Top + $m }
    'top-left'     { $x = $wa.Left + $m;              $y = $wa.Top + $m }
    'center'       { $x = $wa.Left + [int](($wa.Width - $Width) / 2)
                     $y = $wa.Top  + [int](($wa.Height - $Height) / 2) }
    default        { $x = $wa.Right - $Width - $m;    $y = $wa.Bottom - $Height - $m }
  }
  $form.Location = New-Object System.Drawing.Point($x, $y)

  # Hairline border, since a borderless form has no edge of its own.
  $form.Add_Paint({
    param($s, $e)
    $pen = New-Object System.Drawing.Pen $script:CcTheme.Border
    $e.Graphics.DrawRectangle($pen, 0, 0, $s.Width - 1, $s.Height - 1)
    $pen.Dispose()
  })

  Set-CcRoundedCorners -Form $form -Radius $Theme.Radius

  return $form
}


function Add-CcAutoClose {
  # The panel never closes on its own from losing focus -- it waits for a
  # click. But the hook that spawned it is killed at 600s, and a panel that
  # outlives its listener is a dead window whose buttons reach nobody. Close
  # a little before that so the fallback to the terminal stays in step.
  param($Form, $Theme)
  if ($Theme.AutoClose -le 0) { return }

  # Everything an event handler touches must live in script scope. A local
  # would be gone by the time the handler runs -- this function has long
  # since returned -- and calling a method on it throws at event time, where
  # the failure surfaces as a .NET error dialog stealing the modal focus.
  $script:ccTimer          = New-Object System.Windows.Forms.Timer
  $script:ccTimer.Interval = [int]($Theme.AutoClose * 1000)
  $script:ccTimer.Add_Tick({
    $script:ccTimer.Stop()
    $script:form.Close()
  })
  # Safe to start before ShowDialog: the timer only ticks once the message
  # loop is running, which ShowDialog provides.
  $script:ccTimer.Start()
}


function New-CcHeader {
  param([string]$Text, $Theme, [int]$Width)

  $lbl           = New-Object System.Windows.Forms.Label
  $lbl.Text      = $Text
  $lbl.ForeColor = $Theme.Muted
  $lbl.Font      = New-Object System.Drawing.Font($Theme.Font, ($Theme.FontSize - 1.5), [System.Drawing.FontStyle]::Bold)
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
  $b.Font                     = New-Object System.Drawing.Font($Theme.Font, $Theme.FontSize)
  $b.FlatAppearance.BorderSize = 1

  if ($Primary) {
    $b.BackColor                  = $Theme.Accent
    $b.ForeColor                  = $Theme.AccentTxt
    $b.FlatAppearance.BorderColor = $Theme.Accent
  } else {
    $b.BackColor                  = $Theme.BtnBack
    $b.ForeColor                  = $Theme.BtnText
    $b.FlatAppearance.BorderColor = $Theme.Border
  }
  return $b
}
