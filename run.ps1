<#
.SYNOPSIS
    Project CLI: setup, doctor, status, validate, test, verify, package, clean.

.DESCRIPTION
    Thin Windows launcher.  All command behaviour lives in
    <tool root>/scripts/cli.py so that Windows and POSIX runs cannot drift apart.
    This file is deliberately ASCII-only: Windows PowerShell 5.1 decodes a
    BOM-less script as ANSI, and non-ASCII bytes made the earlier version fail to
    parse at all.

    Human Gate approval is NOT available through this CLI.  Gate decisions are
    recorded only by scripts/gate_control.py after an explicit human decision.

.PARAMETER Command
    setup | doctor | status | validate | test | verify | package | clean |
    skills | agents | gates | info | route | plan | hash | compliance |
    git-status | help

.EXAMPLE
    .\run.ps1 doctor
    Check the interpreter, dependencies and external tools.

.EXAMPLE
    .\run.ps1 validate
    Run structure and contract validation.

.EXAMPLE
    .\run.ps1 verify --with-tests
    Full deterministic verification including the pytest suite.
#>
param(
    [Parameter(Position = 0)]
    [string]$Command = 'help',

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot

# Locate the tool root ('90_*') without embedding non-ASCII bytes in this file.
$toolsDir = Get-ChildItem -LiteralPath $repoRoot -Directory -Filter '90_*' -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $toolsDir) {
    Write-Error "Cannot locate the tool root (a '90_*' directory) under $repoRoot."
    exit 2
}
$toolsRoot = $toolsDir.FullName
$cli = Join-Path $toolsRoot 'scripts\cli.py'

$python = $null
foreach ($relative in @('.venv\Scripts\python.exe', '.venv\bin\python')) {
    $candidate = Join-Path $repoRoot $relative
    if (Test-Path -LiteralPath $candidate) { $python = $candidate; break }
}

if (-not $python) {
    Write-Host 'Project Python is missing.' -ForegroundColor Yellow
    Write-Host "  expected: $(Join-Path $repoRoot '.venv\Scripts\python.exe')"
    Write-Host ''
    Write-Host 'Run the setup step first:'
    Write-Host '  PowerShell :  .\setup.ps1'
    Write-Host '  cmd.exe    :  setup.ps1'
    Write-Host '  Git Bash   :  ./setup.sh'
    exit 2
}

$env:UV_CACHE_DIR = Join-Path $toolsRoot '.cache\uv'
$env:PYTHONDONTWRITEBYTECODE = '1'
# Force UTF-8 streams: this repository prints non-ASCII paths, and a cp1252
# console (default on some CI runners) would raise UnicodeEncodeError.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
# Keep UTF-8 output intact on Windows PowerShell 5.1 consoles.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

Push-Location $repoRoot
try {
    & $python $cli $Command @Args
    $exitCode = $LASTEXITCODE
    if ($null -eq $exitCode) { $exitCode = 0 }
} finally {
    Pop-Location
}

exit $exitCode
