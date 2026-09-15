<#
.SYNOPSIS
    Create or refresh the project virtual environment.

.DESCRIPTION
    Idempotent bootstrap entry point.  Finds a Python interpreter that satisfies
    the version range declared in pyproject.toml, creates .venv, installs the
    required dependencies (plus any optional groups you ask for), and runs the
    environment doctor.

    Safe to run repeatedly; already-correct environments are detected and reused.

.EXAMPLE
    .\setup.ps1
    Create .venv and install required dependencies.

.EXAMPLE
    .\setup.ps1 -WithExtras document,visualization
    Also install the optional document and visualization groups.

.EXAMPLE
    .\setup.ps1 -ForceRecreate
    Delete and rebuild .venv (use after switching Python or a broken environment).
#>
param(
    [switch]$DryRun,
    [switch]$Ci,
    [string[]]$WithExtras = @(),
    [switch]$ForceRecreate,
    [switch]$NoDoctor,
    [ValidateSet('auto', 'uv', 'pip')]
    [string]$Installer = 'auto'
)

$ErrorActionPreference = 'Stop'

# This wrapper is ASCII-only on purpose: Windows PowerShell 5.1 decodes a
# BOM-less script as ANSI, so non-ASCII bytes here would break parsing.
# Non-ASCII paths are discovered from workspace-layout.yaml by bootstrap.py.
function Get-ToolsRoot {
    param([string]$RepoRoot)
    $candidates = Get-ChildItem -LiteralPath $RepoRoot -Directory -Filter '90_*' -ErrorAction SilentlyContinue
    if (-not $candidates) {
        throw "Cannot locate the tool root (a '90_*' directory) under $RepoRoot."
    }
    return $candidates[0].FullName
}

function Find-Python {
    $probe = @()
    if ($env:OS -eq 'Windows_NT') {
        $probe += , @('py', '-3')
        $probe += , @('py')
    }
    $probe += , @('python3')
    $probe += , @('python')
    foreach ($candidate in $probe) {
        $exe = Get-Command $candidate[0] -ErrorAction SilentlyContinue
        if (-not $exe) { continue }
        try {
            $args = @()
            if ($candidate.Count -gt 1) { $args = $candidate[1..($candidate.Count - 1)] }
            $null = & $exe.Source @args -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { return $exe.Source }
        } catch {
            continue
        }
    }
    return $null
}

$repoRoot = $PSScriptRoot
$toolsRoot = Get-ToolsRoot -RepoRoot $repoRoot

$python = Find-Python
if (-not $python) {
    Write-Host 'setup: FAIL' -ForegroundColor Red
    Write-Host 'No suitable Python interpreter was found on PATH.'
    Write-Host 'This project requires:'
    Get-Content -LiteralPath (Join-Path $repoRoot 'pyproject.toml') |
        Where-Object { $_ -match 'requires-python' } |
        ForEach-Object { Write-Host ("  " + $_.Trim()) }
    Write-Host 'Install a supported Python 3 (python.org or your package manager), then re-run this script.'
    exit 1
}

$bootstrapArgs = @((Join-Path $toolsRoot 'scripts\bootstrap.py'))
if ($DryRun) { $bootstrapArgs += '--dry-run' }
if ($Ci) { $bootstrapArgs += '--ci' }
foreach ($group in $WithExtras) {
    foreach ($part in ($group -split ',')) {
        if ($part.Trim()) { $bootstrapArgs += @('--with-extras', $part.Trim()) }
    }
}
if ($ForceRecreate) { $bootstrapArgs += '--force-recreate' }
if ($NoDoctor) { $bootstrapArgs += '--no-doctor' }
$bootstrapArgs += @('--installer', $Installer)

Push-Location $repoRoot
try {
    & $python @bootstrapArgs
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $code
