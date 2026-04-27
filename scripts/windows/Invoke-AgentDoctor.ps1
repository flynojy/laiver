[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot "Common.ps1")

$projectRoot = Get-AgentProjectRoot
$envPath = Join-Path $projectRoot ".env"

$checks = @(
  [PSCustomObject]@{ Name = "Node.js"; Required = $true; Available = (Test-AgentCommand -Name "node") },
  [PSCustomObject]@{ Name = "npm.cmd"; Required = $true; Available = (Test-AgentCommand -Name "npm.cmd") },
  [PSCustomObject]@{ Name = "Python"; Required = $true; Available = (Test-AgentCommand -Name "python") },
  [PSCustomObject]@{ Name = "Docker"; Required = $true; Available = (Test-AgentCommand -Name "docker") },
  [PSCustomObject]@{ Name = ".env"; Required = $true; Available = (Test-Path $envPath) },
  [PSCustomObject]@{ Name = "ngrok"; Required = $false; Available = (Test-AgentCommand -Name "ngrok") },
  [PSCustomObject]@{ Name = "cloudflared"; Required = $false; Available = (Test-AgentCommand -Name "cloudflared") }
)

$checks | Format-Table -AutoSize

$missingRequired = @($checks | Where-Object { $_.Required -and -not $_.Available })
if ($missingRequired.Count -gt 0) {
  $names = ($missingRequired | ForEach-Object { $_.Name }) -join ", "
  Write-Error "Missing required Windows tools: $names"
  exit 1
}

Write-Host "Windows-first prerequisites look good."
