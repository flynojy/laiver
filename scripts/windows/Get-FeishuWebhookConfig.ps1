[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ConnectorId,
  [Parameter(Mandatory = $true)]
  [string]$PublicBaseUrl,
  [string]$VerificationToken = "change-me",
  [ValidateSet("webhook", "openapi")]
  [string]$DeliveryMode = "webhook"
)

$normalizedBaseUrl = $PublicBaseUrl.TrimEnd("/")
$callbackUrl = "$normalizedBaseUrl/api/v1/connectors/feishu/webhook/$ConnectorId"

$config = [ordered]@{
  mode = "live"
  delivery_mode = $DeliveryMode
  verification_token = $VerificationToken
  reply_webhook_url = ""
  app_id = ""
  app_secret = ""
  receive_id_type = "chat_id"
  openapi_base_url = "https://open.feishu.cn"
  force_delivery_failure = $false
}

[PSCustomObject]@{
  CallbackUrl = $callbackUrl
  VerificationToken = $VerificationToken
  DeliveryMode = $DeliveryMode
} | Format-List

Write-Host ""
Write-Host "Connector config draft:"
$config | ConvertTo-Json -Depth 5
