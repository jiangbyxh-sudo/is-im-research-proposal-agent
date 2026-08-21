param(
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 8765
)

$proposalSecureKey = Read-Host "DeepSeek API Key" -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new("", $proposalSecureKey).Password
$env:DEEPSEEK_BASE_URL = "https://api.deepseek.com"
$env:DEEPSEEK_MODEL = "deepseek-v4-pro"
$env:PROPOSAL_ENABLE_CHINESE_RETRIEVAL = "1"

try {
    python "$PSScriptRoot\server.py" --host $ListenHost --port $Port
}
finally {
    Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
}
