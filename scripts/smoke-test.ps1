[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$BaseUrl,

    [string]$ExpectedVersion = "",

    [ValidateSet("", "blue", "green")]
    [string]$ExpectedColor = "",

    [ValidateRange(1, 30)]
    [int]$RetryCount = 10,

    [ValidateRange(1, 30)]
    [int]$RetryDelaySeconds = 2
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$BaseUrl = $BaseUrl.TrimEnd("/")
$parsedBaseUrl = $null
if (-not [Uri]::TryCreate($BaseUrl, [UriKind]::Absolute, [ref]$parsedBaseUrl) -or
    $parsedBaseUrl.Scheme -notin @("http", "https")) {
    throw "BaseUrl debe ser una URL absoluta http/https. Valor recibido: '$BaseUrl'."
}

function Invoke-Endpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [switch]$Retry
    )

    $attempts = if ($Retry) { $RetryCount } else { 1 }
    $lastError = $null

    for ($attempt = 1; $attempt -le $attempts; $attempt++) {
        try {
            return Invoke-RestMethod -Uri "$BaseUrl$Path" -Method Get -TimeoutSec 10
        }
        catch {
            $lastError = $_
            if ($attempt -lt $attempts) {
                Write-Host "Intento $attempt/$attempts para $Path fallo; reintentando..."
                Start-Sleep -Seconds $RetryDelaySeconds
            }
        }
    }

    throw "No se pudo consultar $Path despues de $attempts intento(s): $($lastError.Exception.Message)"
}

function Write-Check {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    Write-Host "[OK] $Name" -ForegroundColor Green
}

$health = Invoke-Endpoint -Path "/health" -Retry
if ($health.status -ne "ok") {
    throw "/health devolvio un estado inesperado: '$($health.status)'."
}
Write-Check "Health status=ok"

$version = Invoke-Endpoint -Path "/version"
foreach ($requiredProperty in @("version", "color", "hostname")) {
    if (-not $version.PSObject.Properties.Name.Contains($requiredProperty) -or
        [string]::IsNullOrWhiteSpace([string]$version.$requiredProperty)) {
        throw "/version no contiene un valor valido para '$requiredProperty'."
    }
}

if ($ExpectedVersion -and $version.version -ne $ExpectedVersion) {
    throw "Version inesperada: se esperaba '$ExpectedVersion' y se recibio '$($version.version)'."
}
if ($ExpectedColor -and $version.color -ne $ExpectedColor) {
    throw "Color inesperado: se esperaba '$ExpectedColor' y se recibio '$($version.color)'."
}
Write-Check "Version=$($version.version) Color=$($version.color) Pod=$($version.hostname)"

$products = Invoke-Endpoint -Path "/api/products"
$productList = @($products)
Write-Check "Products respondio correctamente ($($productList.Count) producto(s))"

Write-Host "Smoke test completado correctamente para $BaseUrl."
