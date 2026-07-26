# Guia de contribucion - Jordy

Esta guia define una contribucion funcional y verificable para que Jordy participe directamente en el repositorio del examen final de CI/CD.

## Objetivo de la contribucion

Jordy implementara dos automatizaciones en PowerShell:

1. `scripts/switch-blue-green.ps1`: cambia el trafico del Service `inventario-blue-green` entre BLUE y GREEN, valida que el Deployment objetivo este disponible y confirma el selector final.
2. `scripts/smoke-test.ps1`: ejecuta pruebas rapidas contra `/health`, `/version` y `/api/products` y termina con error si alguna validacion falla.

La contribucion no es solo documentacion: ambos scripts deben ejecutarse realmente sobre Minikube y quedar versionados en Git.

---

## 1. Preparacion

### Opcion recomendada: trabajar en una rama propia

Clonar el repositorio:

```powershell
git clone https://github.com/UPSGabriel/inventario-app-cicd-final.git
cd inventario-app-cicd-final
```

Configurar identidad Git de Jordy en este repositorio:

```powershell
git config user.name "Jordy Espinoza"
git config user.email "CORREO_DE_JORDY_EN_GITHUB"
```

Crear la rama:

```powershell
git switch -c jordy/automatizacion-blue-green
```

Antes de programar verificar:

```powershell
git status
kubectl cluster-info
kubectl get deployments
kubectl get svc inventario-blue-green
kubectl get pods -l app=inventario-bg --show-labels
```

Debe existir:

- `inventario-app-blue`
- `inventario-app-green`
- Service `inventario-blue-green`

---

## 2. Funcionalidad 1 - switch-blue-green.ps1

Crear la carpeta si no existe:

```powershell
New-Item -ItemType Directory -Force scripts
```

Crear `scripts/switch-blue-green.ps1` con esta funcionalidad minima:

- Recibir un parametro obligatorio `blue` o `green`.
- Traducir el destino al Deployment correspondiente.
- Esperar que el Deployment objetivo este disponible.
- Cambiar el selector del Service con `kubectl set selector`.
- Confirmar que `.spec.selector.slot` quedo en el destino solicitado.
- Mostrar los endpoints actuales del Service.
- Terminar con codigo distinto de cero si una validacion falla.

Plantilla sugerida para que Jordy la implemente y comprenda:

```powershell
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("blue", "green")]
    [string]$Target
)

$ErrorActionPreference = "Stop"

$deployment = if ($Target -eq "blue") {
    "inventario-app-blue"
} else {
    "inventario-app-green"
}

Write-Host "Esperando disponibilidad de $deployment..."
kubectl wait --for=condition=Available "deployment/$deployment" --timeout=120s
if ($LASTEXITCODE -ne 0) {
    throw "El Deployment $deployment no esta disponible. No se cambia el trafico."
}

Write-Host "Cambiando Service a slot=$Target..."
kubectl set selector service/inventario-blue-green "app=inventario-bg,slot=$Target"
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo cambiar el selector del Service."
}

$current = kubectl get svc inventario-blue-green -o jsonpath="{.spec.selector.slot}"
if ($current -ne $Target) {
    throw "Validacion fallida. Se esperaba '$Target' y Kubernetes reporta '$current'."
}

Write-Host "Selector activo: $current"
kubectl get endpoints inventario-blue-green
Write-Host "Cambio Blue-Green completado correctamente."
```

### Prueba funcional

Con los cuatro pods BLUE/GREEN levantados:

```powershell
.\scripts\switch-blue-green.ps1 green
kubectl get svc inventario-blue-green -o jsonpath="{.spec.selector.slot}"
```

Debe salir `green`.

Luego:

```powershell
.\scripts\switch-blue-green.ps1 blue
kubectl get svc inventario-blue-green -o jsonpath="{.spec.selector.slot}"
```

Debe salir `blue`.

Guardar captura de ambas ejecuciones.

### Primer commit de Jordy

```powershell
git add scripts/switch-blue-green.ps1
git commit -m "Agregar automatizacion de cambio Blue-Green"
```

---

## 3. Funcionalidad 2 - smoke-test.ps1

Crear `scripts/smoke-test.ps1`.

Debe recibir la URL base del servicio y comprobar:

- `GET /health` devuelve `status=ok`.
- `GET /version` contiene `version`, `color` y `hostname`.
- `GET /api/products` responde correctamente y devuelve una coleccion.
- Si una comprobacion falla, el script debe terminar con error.

Implementacion sugerida:

```powershell
param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl
)

$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd("/")

function Invoke-Check {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    try {
        & $Action
        Write-Host "[OK] $Name"
    }
    catch {
        Write-Error "[FAIL] $Name - $($_.Exception.Message)"
        exit 1
    }
}

Invoke-Check "Health" {
    $health = Invoke-RestMethod "$BaseUrl/health"
    if ($health.status -ne "ok") {
        throw "Estado inesperado: $($health.status)"
    }
}

Invoke-Check "Version" {
    $version = Invoke-RestMethod "$BaseUrl/version"
    if (-not $version.version -or -not $version.color -or -not $version.hostname) {
        throw "Respuesta /version incompleta"
    }
    Write-Host "Version=$($version.version) Color=$($version.color) Pod=$($version.hostname)"
}

Invoke-Check "Products" {
    $products = Invoke-RestMethod "$BaseUrl/api/products"
    if ($null -eq $products) {
        throw "No se recibio una coleccion de productos"
    }
    Write-Host "Productos recibidos: $(@($products).Count)"
}

Write-Host "Smoke test completado correctamente."
```

### Prueba funcional

Abrir el tunel del Service en una terminal aparte:

```powershell
minikube service inventario-blue-green --url
```

Mantener esa terminal abierta. Copiar la URL que entregue Minikube, por ejemplo:

```text
http://127.0.0.1:50475
```

En otra terminal:

```powershell
.\scripts\smoke-test.ps1 -BaseUrl "http://127.0.0.1:50475"
```

Debe mostrar tres comprobaciones `[OK]` y finalizar sin error.

Guardar captura.

### Segundo commit de Jordy

```powershell
git add scripts/smoke-test.ps1
git commit -m "Agregar smoke test del despliegue Kubernetes"
```

---

## 4. Evidencia de autor y trabajo real

Comprobar los commits:

```powershell
git log --oneline --decorate -5
git log -2 --format="%h | %an | %ae | %s"
```

Las dos contribuciones deben aparecer con la identidad Git de Jordy.

Verificar estado:

```powershell
git status
```

Debe terminar limpio.

---

## 5. Subir la rama

```powershell
git push -u origin jordy/automatizacion-blue-green
```

Crear un Pull Request hacia `main` y explicar brevemente:

- automatizacion del corte Blue-Green;
- validacion previa del Deployment objetivo;
- smoke test de endpoints despues del despliegue;
- evidencia de ejecucion en Minikube.

Despues de integrar el PR, actualizar localmente:

```powershell
git switch main
git pull origin main
```

---

## 6. Que debe poder explicar Jordy al profesor

### ¿Que hace switch-blue-green.ps1?

Automatiza el cambio del selector del Service entre `slot=blue` y `slot=green`. Antes de mover el trafico valida que el Deployment objetivo este disponible, reduciendo el riesgo de enviar peticiones a una version que aun no esta lista.

### ¿Por que no elimina el Deployment anterior?

Porque Blue-Green mantiene las dos versiones disponibles. Esto permite hacer un corte rapido y tambien regresar a la version anterior cambiando nuevamente el selector.

### ¿Que hace smoke-test.ps1?

Realiza una validacion rapida posterior al despliegue. Comprueba salud, version y acceso al catalogo. Si una comprobacion falla devuelve error, por lo que puede reutilizarse manualmente o integrarse posteriormente en CI/CD.

### ¿Como aporta esto al examen?

No reemplaza los manifiestos Blue-Green ya implementados. Los complementa con automatizacion reproducible para el cambio de trafico y la validacion posterior al despliegue.

---

## 7. Checklist final de Jordy

- [ ] Configuro su nombre y correo Git.
- [ ] Creo una rama propia.
- [ ] Implemento `switch-blue-green.ps1`.
- [ ] Probo GREEN y BLUE realmente sobre Minikube.
- [ ] Hizo el primer commit con su autor.
- [ ] Implemento `smoke-test.ps1`.
- [ ] Ejecuto el smoke test contra el Service.
- [ ] Hizo el segundo commit con su autor.
- [ ] Guardo capturas de la ejecucion.
- [ ] Subio su rama y creo/integro el Pull Request.
- [ ] Puede explicar ambos scripts sin leer el codigo completo.
