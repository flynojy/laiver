[CmdletBinding()]
param(
  [int]$ApiPort = 8000,
  [int]$WebPort = 3000,
  [switch]$IncludeDocker
)

. (Join-Path $PSScriptRoot "Common.ps1")

function New-AgentCheck {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Status,
    [Parameter(Mandatory = $true)][string]$Detail,
    [bool]$Required = $true
  )

  return [PSCustomObject]@{
    Name = $Name
    Required = $Required
    Status = $Status
    Detail = $Detail
  }
}

function Test-AgentPythonDependencies {
  param([Parameter(Mandatory = $true)][string]$Python)

  try {
    & $Python -c "import fastapi, uvicorn, sqlalchemy, pydantic, httpx" | Out-Null
    return $true
  }
  catch {
    return $false
  }
}

$projectRoot = Get-AgentProjectRoot
$envPath = Join-Path $projectRoot ".env"
$envExamplePath = Join-Path $projectRoot ".env.example"
$nodeModulesPath = Join-Path $projectRoot "node_modules"
$sqlitePath = Join-Path $projectRoot "apps\api\local.db"
$sqliteDir = Split-Path $sqlitePath -Parent
$apiHealthUrl = "http://127.0.0.1:$ApiPort/api/v1/health"
$webUrl = "http://127.0.0.1:$WebPort"

$checks = New-Object System.Collections.Generic.List[object]

try {
  $python = Resolve-AgentPython
  $pythonVersion = (& $python --version).Trim()
  $checks.Add((New-AgentCheck -Name "Python" -Status "OK" -Detail "$pythonVersion at $python"))
  if (Test-AgentPythonDependencies -Python $python) {
    $checks.Add((New-AgentCheck -Name "Python deps" -Status "OK" -Detail "FastAPI backend dependencies are importable."))
  }
  else {
    $checks.Add((New-AgentCheck -Name "Python deps" -Status "FAIL" -Detail "Run: .\.venv\Scripts\Activate.ps1; python -m pip install -e `"apps/api[dev]`""))
  }
}
catch {
  $checks.Add((New-AgentCheck -Name "Python" -Status "FAIL" -Detail $_.Exception.Message))
}

try {
  $npm = Resolve-AgentNpm
  $node = Get-Command "node" -ErrorAction Stop
  $nodeVersion = (& $node.Source -p "process.versions.node").Trim()
  $npmVersion = (& $npm -v).Trim()
  $checks.Add((New-AgentCheck -Name "Node.js" -Status "OK" -Detail "Node $nodeVersion, npm $npmVersion"))
}
catch {
  $checks.Add((New-AgentCheck -Name "Node.js" -Status "FAIL" -Detail $_.Exception.Message))
}

if (Test-Path $nodeModulesPath) {
  $checks.Add((New-AgentCheck -Name "npm deps" -Status "OK" -Detail "node_modules exists."))
}
else {
  $checks.Add((New-AgentCheck -Name "npm deps" -Status "FAIL" -Detail "Run: npm.cmd ci"))
}

if (Test-Path $envPath) {
  $checks.Add((New-AgentCheck -Name ".env" -Status "OK" -Detail $envPath))
}
elseif (Test-Path $envExamplePath) {
  $checks.Add((New-AgentCheck -Name ".env" -Status "WARN" -Detail "Missing .env. It can be created from .env.example by the local startup script."))
}
else {
  $checks.Add((New-AgentCheck -Name ".env" -Status "FAIL" -Detail "Missing both .env and .env.example."))
}

try {
  $probe = Join-Path $sqliteDir ".local-write-probe"
  Set-Content -LiteralPath $probe -Value "ok" -Encoding ASCII
  Remove-Item -LiteralPath $probe -Force
  $sqliteDetail = if (Test-Path $sqlitePath) { "SQLite file exists at $sqlitePath" } else { "SQLite directory is writable; DB will be created on startup." }
  $checks.Add((New-AgentCheck -Name "SQLite" -Status "OK" -Detail $sqliteDetail))
}
catch {
  $checks.Add((New-AgentCheck -Name "SQLite" -Status "FAIL" -Detail "SQLite path is not writable: $sqliteDir"))
}

foreach ($portSpec in @(
  [PSCustomObject]@{ Name = "API port"; Port = $ApiPort; Url = $apiHealthUrl },
  [PSCustomObject]@{ Name = "Web port"; Port = $WebPort; Url = $webUrl }
)) {
  $listeners = @(Get-AgentPortListeners -Port $portSpec.Port)
  if ($listeners.Count -eq 0) {
    $checks.Add((New-AgentCheck -Name $portSpec.Name -Status "OK" -Detail "Port $($portSpec.Port) is free."))
    continue
  }

  if (Test-AgentHttpOk -Url $portSpec.Url) {
    $checks.Add((New-AgentCheck -Name $portSpec.Name -Status "OK" -Detail "Service is already responding at $($portSpec.Url)."))
    continue
  }

  $owners = ($listeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
  $checks.Add((New-AgentCheck -Name $portSpec.Name -Status "WARN" -Detail "Port $($portSpec.Port) is occupied by PID(s): $owners"))
}

if ($IncludeDocker) {
  if (Test-AgentCommand -Name "docker") {
    try {
      $dockerVersion = (& docker info --format "{{.ServerVersion}}" 2>$null).Trim()
      if ([string]::IsNullOrWhiteSpace($dockerVersion)) {
        $checks.Add((New-AgentCheck -Name "Docker" -Status "WARN" -Detail "docker exists, but Docker daemon did not respond." -Required $false))
      }
      else {
        $checks.Add((New-AgentCheck -Name "Docker" -Status "OK" -Detail "Docker daemon $dockerVersion" -Required $false))
      }
    }
    catch {
      $checks.Add((New-AgentCheck -Name "Docker" -Status "WARN" -Detail "docker exists, but Docker daemon did not respond." -Required $false))
    }
  }
  else {
    $checks.Add((New-AgentCheck -Name "Docker" -Status "WARN" -Detail "docker command was not found. Docker is optional for local mode." -Required $false))
  }
}

$checks | Format-Table -AutoSize

$failed = @($checks | Where-Object { $_.Required -and $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
  $names = ($failed | ForEach-Object { $_.Name }) -join ", "
  Write-Error "Local prerequisites failed: $names"
  exit 1
}

$warnings = @($checks | Where-Object { $_.Status -eq "WARN" })
if ($warnings.Count -gt 0) {
  Write-Warning "Doctor completed with warnings. Local startup may still work if the warnings are expected."
  exit 0
}

Write-Host "Laiver local prerequisites look good."
