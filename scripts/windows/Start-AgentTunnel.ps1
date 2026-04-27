[CmdletBinding()]
param(
  [ValidateSet("auto", "ngrok", "cloudflared")]
  [string]$Provider = "auto",
  [int]$Port = 8000
)

. (Join-Path $PSScriptRoot "Common.ps1")

if ($Provider -eq "auto") {
  if (Test-AgentCommand -Name "cloudflared") {
    $Provider = "cloudflared"
  } elseif (Test-AgentCommand -Name "ngrok") {
    $Provider = "ngrok"
  } else {
    throw "Neither cloudflared nor ngrok was found on PATH."
  }
}

if ($Provider -eq "cloudflared") {
  Assert-AgentCommand -Name "cloudflared"
  & cloudflared tunnel --url "http://localhost:$Port"
  exit $LASTEXITCODE
}

Assert-AgentCommand -Name "ngrok"
& ngrok http "http://localhost:$Port"
exit $LASTEXITCODE
