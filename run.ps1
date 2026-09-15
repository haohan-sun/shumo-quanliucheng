param(
    [ValidateSet("status", "validate", "doctor", "hash", "compliance", "pytest", "skills", "agents", "git-status")]
    [string]$Command = "status",
    [switch]$Update
)

$toolRoot = Join-Path $PSScriptRoot "90_工具与配置"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$env:UV_CACHE_DIR = Join-Path $toolRoot ".cache\uv"
$env:PYTHONDONTWRITEBYTECODE = "1"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Project Python is missing: $python"
    exit 2
}

Push-Location $PSScriptRoot
try {
    switch ($Command) {
        "status" { & $python "$toolRoot\scripts\status.py" "--json" }
        "validate" { & $python "$toolRoot\scripts\validate.py" "--with-tests" }
        "doctor" { & $python "$toolRoot\scripts\doctor.py" }
        "hash" {
            if ($Update) { & $python "$toolRoot\scripts\hash_inputs.py" "--update" }
            else { & $python "$toolRoot\scripts\hash_inputs.py" }
        }
        "compliance" { & $python "$toolRoot\scripts\compliance.py" "--json" }
        "pytest" { & $python "-m" "pytest" "-ra" }
        "skills" { Get-ChildItem -LiteralPath "$toolRoot\.agents\skills" -Directory | Sort-Object Name | Select-Object -ExpandProperty Name }
        "agents" { Get-ChildItem -LiteralPath "$toolRoot\.codex\agents" -File | Sort-Object Name | Select-Object -ExpandProperty BaseName }
        "git-status" {
            $safePath = $PSScriptRoot.Replace("\", "/")
            & git -c "safe.directory=$safePath" -C $PSScriptRoot status --short
        }
    }
    $commandExitCode = $LASTEXITCODE
    if ($null -eq $commandExitCode) { $commandExitCode = 0 }
}
finally {
    Pop-Location
}

exit $commandExitCode
