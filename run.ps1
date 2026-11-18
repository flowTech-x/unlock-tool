# MI Bootloader Unlock Tool — Windows Multi-Token Launcher
# Opens one Windows Terminal pane per token automatically

$python = "C:\Users\dasav\AppData\Local\Programs\Python\Python310\python.exe"
$script = Join-Path $PSScriptRoot "script.py"
$tokenFile = Join-Path $PSScriptRoot "token.txt"

if (-not (Test-Path $tokenFile)) {
    Write-Host "ERROR: token.txt not found!" -ForegroundColor Red
    pause; exit 1
}

$tokens = Get-Content $tokenFile | Where-Object { $_.Trim() -ne "" }
$count  = $tokens.Count

Write-Host ""
Write-Host "  MI Bootloader Unlock Tool" -ForegroundColor Cyan
Write-Host "  ─────────────────────────" -ForegroundColor DarkCyan
Write-Host "  Tokens detected: $count" -ForegroundColor Yellow
Write-Host ""
Write-Host "  [1] Run a single token (choose which one)"    -ForegroundColor White
Write-Host "  [2] Run ALL $count token(s) in separate windows" -ForegroundColor White
Write-Host ""

$mode = Read-Host "  Select mode"

if ($mode -eq "2") {
    # Launch one Windows Terminal tab per token
    $wtAvail = Get-Command wt -ErrorAction SilentlyContinue
    if ($wtAvail) {
        $cmd = "wt"
        for ($i = 1; $i -le $count; $i++) {
            $pane = "new-tab pwsh -NoExit -Command `"cd '$PSScriptRoot'; echo $i | & '$python' '$script'`""
            if ($i -gt 1) { $pane = "; " + $pane }
            $cmd += " " + $pane
        }
        Write-Host "  Launching $count tabs in Windows Terminal..." -ForegroundColor Green
        Start-Process "wt" -ArgumentList ($cmd -replace '^wt ', '')
    } else {
        # Fallback: separate PowerShell windows
        for ($i = 1; $i -le $count; $i++) {
            Start-Process "pwsh" -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; echo $i | & '$python' '$script'"
        }
        Write-Host "  Launched $count PowerShell windows." -ForegroundColor Green
    }
} else {
    # Single token mode — let script handle selection
    Write-Host ""
    Set-Location $PSScriptRoot
    & $python $script
}
