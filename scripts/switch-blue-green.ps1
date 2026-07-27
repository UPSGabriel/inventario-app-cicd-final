[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("blue", "green")]
    [string]$Target,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Context,

    [ValidateNotNullOrEmpty()]
    [string]$Namespace = "default",

    [ValidateRange(10, 600)]
    [int]$TimeoutSeconds = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    throw "kubectl no esta disponible en PATH."
}

# El contexto se resuelve una sola vez y se pasa a todas las invocaciones. Esto evita
# que otro proceso cambie el contexto global entre la validacion y el corte de trafico.
$kubectlBaseArgs = @("--context", $Context, "--namespace", $Namespace)

function Invoke-KubectlCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$CommandArgs
    )

    $previousErrorAction = $ErrorActionPreference
    try {
        # Windows PowerShell 5.1 transforma stderr nativo en ErrorRecord. Kubectl puede
        # emitir advertencias con exit code 0, por lo que decidimos por codigo de salida.
        $ErrorActionPreference = "Continue"
        $output = & kubectl @kubectlBaseArgs @CommandArgs 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
    }

    foreach ($line in @($output)) {
        if ($line -is [System.Management.Automation.ErrorRecord]) {
            Write-Warning $line.ToString()
        }
        else {
            Write-Host $line
        }
    }

    if ($exitCode -ne 0) {
        throw "kubectl fallo: kubectl $($CommandArgs -join ' ')"
    }
}

function Get-KubectlValue {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$CommandArgs
    )

    $previousErrorAction = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = & kubectl @kubectlBaseArgs @CommandArgs 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
    }

    if ($exitCode -ne 0) {
        throw "kubectl fallo: kubectl $($CommandArgs -join ' ')`n$($output -join [Environment]::NewLine)"
    }

    # Conserva stdout y descarta advertencias de stderr cuando kubectl termino bien.
    $stdout = @($output | Where-Object { $_ -is [string] })
    return (($stdout | Out-String).Trim())
}

function Wait-ServiceEndpointSlice {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ServiceName,

        [Parameter(Mandatory = $true)]
        [ValidateSet("blue", "green")]
        [string]$ExpectedSlot,

        [Parameter(Mandatory = $true)]
        [int]$WaitSeconds
    )

    $deadline = (Get-Date).AddSeconds($WaitSeconds)
    $lastObservation = "sin endpoints"
    do {
        try {
            $rawEndpointPods = Get-KubectlValue @(
                "get",
                "endpointslices.discovery.k8s.io",
                "--selector",
                "kubernetes.io/service-name=$ServiceName",
                "-o",
                "jsonpath={range .items[*].endpoints[*]}{.targetRef.name}{'\n'}{end}"
            )
            $endpointPods = @($rawEndpointPods -split "\r?\n" | Where-Object { $_ } | Sort-Object -Unique)
            $converged = $endpointPods.Count -gt 0
            $lastObservation = if ($endpointPods.Count) {
                "pods=" + ($endpointPods -join ",")
            }
            else {
                "sin endpoints"
            }

            foreach ($podName in $endpointPods) {
                try {
                    $podSlot = Get-KubectlValue @(
                        "get",
                        "pod/$podName",
                        "-o",
                        "jsonpath={.metadata.labels.slot}"
                    )
                }
                catch {
                    $lastObservation = "no se pudo consultar pod/${podName}: $($_.Exception.Message)"
                    $converged = $false
                    break
                }

                if ($podSlot -ne $ExpectedSlot) {
                    $lastObservation = "pod/$podName tiene slot=$podSlot"
                    $converged = $false
                    break
                }
            }

            if ($converged) {
                return $endpointPods
            }
        }
        catch {
            $lastObservation = $_.Exception.Message
        }

        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)

    throw "EndpointSlice no convergio a slot='$ExpectedSlot' en $WaitSeconds segundos. Ultima observacion: $lastObservation"
}

$deployment = "inventario-app-$Target"
$service = "inventario-blue-green"

Write-Host "Contexto fijado: $Context | Namespace: $Namespace"
Write-Host "Esperando que deployment/$deployment este disponible..."
Invoke-KubectlCommand @(
    "wait",
    "--for=condition=Available",
    "deployment/$deployment",
    "--timeout=$($TimeoutSeconds)s"
)

$previousSlot = Get-KubectlValue @(
    "get",
    "service/$service",
    "-o",
    "jsonpath={.spec.selector.slot}"
)

if ($previousSlot -notin @("blue", "green")) {
    throw "El Service tiene un selector slot inesperado: '$previousSlot'. No se cambia el trafico."
}

$selectorChanged = $false
try {
    Write-Host "Cambiando service/$service de slot=$previousSlot a slot=$Target..."
    Invoke-KubectlCommand @(
        "set",
        "selector",
        "service/$service",
        "app=inventario-bg,slot=$Target"
    )
    $selectorChanged = $true

    $current = Get-KubectlValue @(
        "get",
        "service/$service",
        "-o",
        "jsonpath={.spec.selector.slot}"
    )
    if ($current -ne $Target) {
        throw "Se esperaba slot='$Target' y Kubernetes reporta slot='$current'."
    }

    # EndpointSlice reemplaza la API Endpoints obsoleta. La reconciliacion del Service
    # es asincrona: se espera hasta que TODOS los endpoints pertenezcan al slot destino.
    $endpointTimeoutSeconds = [Math]::Min(30, $TimeoutSeconds)
    $endpointPods = @(
        Wait-ServiceEndpointSlice `
            -ServiceName $service `
            -ExpectedSlot $Target `
            -WaitSeconds $endpointTimeoutSeconds
    )

    Write-Host "Selector activo: slot=$current"
    Write-Host "Pods que reciben trafico:"
    $endpointPods | ForEach-Object { Write-Host "  - $_" }
    Write-Host "Cambio Blue-Green completado correctamente."
}
catch {
    $cutoverError = $_.Exception.Message
    if ($selectorChanged -and $previousSlot -ne $Target) {
        Write-Warning "La validacion posterior al corte fallo. Restaurando slot=$previousSlot..."
        try {
            Invoke-KubectlCommand @(
                "set",
                "selector",
                "service/$service",
                "app=inventario-bg,slot=$previousSlot"
            )
            $restoredSlot = Get-KubectlValue @(
                "get",
                "service/$service",
                "-o",
                "jsonpath={.spec.selector.slot}"
            )
            if ($restoredSlot -ne $previousSlot) {
                throw "Kubernetes reporta slot='$restoredSlot' despues del rollback."
            }
            $rollbackPods = @(
                Wait-ServiceEndpointSlice `
                    -ServiceName $service `
                    -ExpectedSlot $previousSlot `
                    -WaitSeconds ([Math]::Min(30, $TimeoutSeconds))
            )
            Write-Host "Rollback convergido a slot=$previousSlot en: $($rollbackPods -join ', ')"
        }
        catch {
            throw "Fallo el corte: $cutoverError. Tambien fallo el rollback a slot='$previousSlot': $($_.Exception.Message)"
        }
    }

    throw "Fallo el corte Blue-Green; selector anterior slot='$previousSlot': $cutoverError"
}
