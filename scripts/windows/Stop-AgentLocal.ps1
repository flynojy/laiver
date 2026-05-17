[CmdletBinding()]
param(
  [int]$ApiPort = 8000,
  [int]$WebPort = 3000,
  [switch]$ForcePorts
)

. (Join-Path $PSScriptRoot "Common.ps1")

function Get-AgentChildProcessIds {
  param([Parameter(Mandatory = $true)][int]$ParentProcessId)

  try {
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $ParentProcessId" -ErrorAction Stop)
  }
  catch {
    return @()
  }

  $ids = New-Object System.Collections.Generic.List[int]
  foreach ($child in $children) {
    $ids.Add([int]$child.ProcessId)
    foreach ($descendantId in (Get-AgentChildProcessIds -ParentProcessId ([int]$child.ProcessId))) {
      $ids.Add([int]$descendantId)
    }
  }
  return @($ids)
}

function Stop-AgentProcessTree {
  param([Parameter(Mandatory = $true)][int]$RootProcessId)

  $childIds = @(Get-AgentChildProcessIds -ParentProcessId $RootProcessId)
  foreach ($childId in ($childIds | Sort-Object -Descending)) {
    Stop-Process -Id $childId -Force -ErrorAction SilentlyContinue
  }
  Stop-Process -Id $RootProcessId -Force -ErrorAction SilentlyContinue
}

function Stop-AgentPort {
  param(
    [Parameter(Mandatory = $true)][int]$Port,
    [Parameter(Mandatory = $true)][string]$Name,
    [string]$HealthUrl = ""
  )

  $listeners = @(Get-AgentPortListeners -Port $Port)
  if ($listeners.Count -eq 0) {
    Write-Host "$Name port $Port is not listening."
    return
  }

  $processIds = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
  foreach ($processId in $processIds) {
    $commandLine = Get-AgentProcessCommandLine -ProcessId $processId
    $looksLocal = Test-AgentProcessLooksLocal -ProcessId $processId
    if (-not $looksLocal -and -not [string]::IsNullOrWhiteSpace($HealthUrl)) {
      $looksLocal = Test-AgentHttpOk -Url $HealthUrl
    }
    if (-not $looksLocal -and -not $ForcePorts) {
      Write-Warning "$Name port $Port is owned by PID $processId, but it does not look like this Laiver project. Use -ForcePorts to stop it."
      if (-not [string]::IsNullOrWhiteSpace($commandLine)) {
        Write-Host "Command line: $commandLine"
      }
      continue
    }

    Write-Host "Stopping $Name on port $Port, PID $processId..."
    Stop-AgentProcessTree -RootProcessId $processId
  }
}

Write-Host "Stopping Laiver local mode..."
$maxAttempts = 4
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
  Stop-AgentPort -Port $ApiPort -Name "API" -HealthUrl "http://127.0.0.1:$ApiPort/api/v1/health"
  Stop-AgentPort -Port $WebPort -Name "Web"

  Start-Sleep -Seconds 1
  if (-not (Test-AgentPortListening -Port $ApiPort) -and -not (Test-AgentPortListening -Port $WebPort)) {
    break
  }
}

Start-Sleep -Seconds 1

$apiStillListening = Test-AgentPortListening -Port $ApiPort
$webStillListening = Test-AgentPortListening -Port $WebPort

if ($apiStillListening -or $webStillListening) {
  Write-Warning "Some local ports are still listening."
  if ($apiStillListening) {
    Write-Warning "API port $ApiPort is still in use."
  }
  if ($webStillListening) {
    Write-Warning "Web port $WebPort is still in use."
  }
  exit 1
}

Write-Host "Laiver local mode stopped."
