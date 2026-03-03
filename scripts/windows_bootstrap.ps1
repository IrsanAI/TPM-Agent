Param(
  [ValidateSet('auto','dev','easy')]
  [string]$Mode = 'auto',
  [int]$Port = 8787
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Write-Step($msg) { Write-Host "[TPM] $msg" -ForegroundColor Cyan }
function Have-Cmd($name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

Write-Step "Detecting environment"
$hasPython = Have-Cmd 'python'
$hasDocker = Have-Cmd 'docker'
$hasCompose = $hasDocker -and ((docker compose version) 2>$null)

if (-not $hasPython -and -not $hasCompose) {
  Write-Host "Python or Docker required. Install one of them first." -ForegroundColor Red
  exit 1
}

if ($Mode -eq 'auto') {
  if ($hasPython) { $Mode = 'dev' } elseif ($hasCompose) { $Mode = 'easy' }
}

if ($Mode -eq 'dev') {
  Write-Step "Developer path: venv + pip + uvicorn runtime"
  if (-not (Test-Path .venv)) { python -m venv .venv }
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  Write-Step "Starting Forge Runtime at http://localhost:$Port"
  python -m uvicorn production.forge_runtime:app --host 0.0.0.0 --port $Port
  exit $LASTEXITCODE
}

if ($Mode -eq 'easy') {
  if (-not $hasCompose) {
    Write-Host "Docker Compose is required for easy mode." -ForegroundColor Red
    exit 1
  }
  Write-Step "Easy path: docker compose up tpm-forge-web"
  docker compose up --build tpm-forge-web
  exit $LASTEXITCODE
}
