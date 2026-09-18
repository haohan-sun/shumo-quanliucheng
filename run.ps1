<#
.SYNOPSIS
    Project CLI: setup, doctor, status, validate, test, lint, verify, package, clean.

.DESCRIPTION
    Thin Windows launcher.  All command behaviour lives in
    <tool root>/scripts/cli.py so that Windows and POSIX runs cannot drift apart.
    This file is deliberately ASCII-only: Windows PowerShell 5.1 decodes a
    BOM-less script as ANSI, and non-ASCII bytes made an earlier version fail to
    parse at all.

    `setup` is handled before the interpreter check and delegated to setup.ps1,
    so the very first command a new user runs works before .venv exists.

    Human Gate approval is NOT available through this CLI.  Gate decisions are
    recorded only by scripts/gate_control.py after an explicit human decision.

.PARAMETER Command
    setup | doctor | status | validate | test | lint | verify | package | clean |
    skills | agents | gates | modes | demo | info | route | plan | hash |
    compliance | git-status | help

.EXAMPLE
    .\run.ps1 setup
    Create .venv and install dependencies (same as .\setup.ps1).

.EXAMPLE
    .\run.ps1 doctor
    Check the interpreter, dependencies and external tools.

.EXAMPLE
    .\run.ps1 verify --with-tests
    Full deterministic verification including the pytest suite.
#>
param(
    [Parameter(Position = 0)]
    [string]$Command = 'help',

    # Named $Arguments, not $Args: $Args is a PowerShell automatic variable, and
    # reusing it made the binder pass options such as --no-doctor as values.
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
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

# ---------------------------------------------------------------------------
# `setup` runs before anything needs the project interpreter.
# ---------------------------------------------------------------------------
if ($Command -in @('setup', 'bootstrap')) {
    $setupScript = Join-Path $repoRoot 'setup.ps1'
    if (-not (Test-Path -LiteralPath $setupScript)) {
        Write-Error "setup.ps1 is missing next to run.ps1; cannot provision the environment."
        exit 2
    }

    $setupParams = @{}
    $showSetupHelp = $false
    $installerChoices = @('auto', 'uv', 'pip')
    for ($index = 0; $index -lt $Arguments.Count; $index++) {
        $token = $Arguments[$index]
        switch -Regex ($token) {
            '^(--?h|--?help)$' { $showSetupHelp = $true; continue }
            '^--?dry-?run$' { $setupParams['DryRun'] = $true; continue }
            '^--?ci$' { $setupParams['Ci'] = $true; continue }
            '^--?force-?recreate$' { $setupParams['ForceRecreate'] = $true; continue }
            '^--?no-?doctor$' { $setupParams['NoDoctor'] = $true; continue }
            '^--?(with-?extras|extras)$' {
                # A missing value must fail, not silently fall back to defaults: a
                # typo would otherwise install a different environment than asked.
                if ($index + 1 -ge $Arguments.Count -or $Arguments[$index + 1].StartsWith('-')) {
                    Write-Host "run.ps1 setup: $token requires a value, e.g. --with-extras document." -ForegroundColor Red
                    exit 2
                }
                $index++
                $setupParams['WithExtras'] = $Arguments[$index] -split ','
                continue
            }
            '^--?installer$' {
                if ($index + 1 -ge $Arguments.Count -or $Arguments[$index + 1].StartsWith('-')) {
                    Write-Host "run.ps1 setup: --installer requires a value: $($installerChoices -join ', ')." -ForegroundColor Red
                    exit 2
                }
                $index++
                $choice = $Arguments[$index]
                if ($installerChoices -notcontains $choice) {
                    Write-Host "run.ps1 setup: --installer must be one of $($installerChoices -join ', ')." -ForegroundColor Red
                    exit 2
                }
                $setupParams['Installer'] = $choice
                continue
            }
            default {
                # Unknown input is refused rather than ignored, so a typo such as
                # --force-recraete cannot silently run a normal setup. This matches
                # setup.sh, which forwards to bootstrap.py where argparse exits 2.
                if ($token.StartsWith('-')) {
                    Write-Host "run.ps1 setup: unknown option '$token'." -ForegroundColor Red
                } else {
                    Write-Host "run.ps1 setup: unexpected argument '$token'." -ForegroundColor Red
                }
                Write-Host "Run '.\run.ps1 setup --help' to see the supported options." -ForegroundColor Red
                exit 2
            }
        }
    }

    if ($showSetupHelp) {
        Get-Help $setupScript -Detailed
        exit 0
    }

    # Splat the hashtable so the tokens bind as named parameters. Passing a plain
    # string array to a script with non-positional parameters binds 'x' as the
    # literal value of $DryRun, which PowerShell rejects.
    & $setupScript @setupParams
    exit $LASTEXITCODE
}

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
    Write-Host '  PowerShell :  .\run.ps1 setup'
    Write-Host '  or         :  .\setup.ps1'
    Write-Host '  cmd.exe    :  run.ps1 setup'
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
    & $python $cli $Command @Arguments
    $exitCode = $LASTEXITCODE
    if ($null -eq $exitCode) { $exitCode = 0 }
} finally {
    Pop-Location
}

exit $exitCode
