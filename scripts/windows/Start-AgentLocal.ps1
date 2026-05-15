[CmdletBinding()]
param(
  [int]$ApiPort = 8000,
  [int]$WebPort = 3000,
  [switch]$CheckOllama,
  [string]$OllamaModel = "qwen3:14b",
  [int]$OllamaNumCtx = 1024,
  [int]$OllamaNumPredict = 32,
  [switch]$SkipOllamaGenerate,
  [switch]$NoBrowser,
  [switch]$Detach
)

. (Join-Path $PSScriptRoot "Common.ps1")

$projectRoot = Get-AgentProjectRoot
$logRoot = Join-Path $projectRoot ".tmp\run-logs"
New-Item -ItemType Directory -Force $logRoot | Out-Null

$python = Resolve-AgentPython
$npm = Resolve-AgentNpm
Ensure-AgentEnvFile | Out-Null
Import-AgentDotEnv -Overwrite

$env:DATABASE_URL = "sqlite:///./apps/api/local.db"
$env:AUTO_INIT_DB = "true"
$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:$ApiPort/api/v1"
$env:CORS_ORIGINS = "http://localhost:$WebPort,http://127.0.0.1:$WebPort"

$apiHealthUrl = "http://127.0.0.1:$ApiPort/api/v1/health"
$webUrl = "http://127.0.0.1:$WebPort"
$apiOut = Join-Path $logRoot "local-api.out.log"
$apiErr = Join-Path $logRoot "local-api.err.log"
$webOut = Join-Path $logRoot "local-web.out.log"
$webErr = Join-Path $logRoot "local-web.err.log"
$startedProcesses = @()

Write-Host "Laiver local startup"
Write-Host "Project: $projectRoot"
Write-Host "Python: $python"
Write-Host "npm: $npm"
Write-Host "Database: SQLite at apps/api/local.db"

if ($CheckOllama) {
  Write-Host "Checking Ollama model before startup..."
  $ollamaArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $PSScriptRoot "Invoke-OllamaCheck.ps1"),
    "-Model", $OllamaModel,
    "-NumCtx", "$OllamaNumCtx",
    "-NumPredict", "$OllamaNumPredict"
  )
  if ($SkipOllamaGenerate) {
    $ollamaArgs += "-SkipGenerate"
  }
  & powershell @ollamaArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Ollama preflight failed. Startup stopped because -CheckOllama was requested."
  }
}

if (Test-AgentHttpOk -Url $apiHealthUrl) {
  Write-Host "API already healthy at $apiHealthUrl"
}
elseif (Test-AgentPortListening -Port $ApiPort) {
  throw "Port $ApiPort is already in use, but $apiHealthUrl is not healthy. Stop the process on that port or choose -ApiPort."
}
else {
  Write-Host "Starting API on port $ApiPort..."
  $apiProcess = Start-Process `
    -FilePath $python `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "$ApiPort", "--app-dir", "apps/api") `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $apiOut `
    -RedirectStandardError $apiErr `
    -WindowStyle Hidden `
    -PassThru
  $startedProcesses += $apiProcess
}

if (-not (Wait-AgentHttpOk -Url $apiHealthUrl -TimeoutSeconds 45)) {
  Write-Host "API failed to become healthy. Last error log lines:"
  if (Test-Path $apiErr) {
    Get-Content $apiErr -Tail 30
  }
  throw "API startup failed. See $apiErr"
}

if (Test-AgentHttpOk -Url $webUrl) {
  Write-Host "Web already available at $webUrl"
}
elseif (Test-AgentPortListening -Port $WebPort) {
  throw "Port $WebPort is already in use, but $webUrl is not responding. Stop the process on that port or choose -WebPort."
}
else {
  Write-Host "Starting Web on port $WebPort..."
  $env:PORT = "$WebPort"
  $webProcess = Start-Process `
    -FilePath $npm `
    -ArgumentList @("run", "dev:web") `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $webOut `
    -RedirectStandardError $webErr `
    -WindowStyle Hidden `
    -PassThru
  $startedProcesses += $webProcess
}

if (-not (Wait-AgentHttpOk -Url $webUrl -TimeoutSeconds 60)) {
  Write-Host "Web failed to become available. Last error log lines:"
  if (Test-Path $webErr) {
    Get-Content $webErr -Tail 30
  }
  throw "Web startup failed. See $webErr"
}

Write-Host ""
Write-Host "Laiver local mode is running."
Write-Host "Web:        http://localhost:$WebPort"
Write-Host "Onboarding: http://localhost:$WebPort/onboarding"
Write-Host "API:        http://127.0.0.1:$ApiPort/api/v1"
Write-Host "API docs:   http://127.0.0.1:$ApiPort/docs"
Write-Host "Logs:       $logRoot"

if (-not $NoBrowser) {
  Start-Process "http://localhost:$WebPort" | Out-Null
}

if ($Detach) {
  Write-Host "Detached mode enabled. Processes will keep running independently in a normal PowerShell session."
  exit 0
}

Write-Host ""
Write-Host "This window is supervising the local Laiver process. Press Ctrl+C to stop processes started by this script."

try {
  while ($true) {
    foreach ($process in $startedProcesses) {
      if ($process.HasExited) {
        throw "A started process exited unexpectedly. Check logs in $logRoot"
      }
    }
    Start-Sleep -Seconds 5
  }
}
finally {
  foreach ($process in $startedProcesses) {
    if (-not $process.HasExited) {
      Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
  }
}
