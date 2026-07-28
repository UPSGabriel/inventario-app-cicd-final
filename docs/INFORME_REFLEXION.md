# Informe de reflexion - Practica CI/CD

**Integrantes:** Gabriel Alexander Cordova Solorzano y Jordy Espinoza  
**Repositorio:** <https://github.com/UPSGabriel/inventario-app-cicd-final>  
**Fecha de corte:** 28 de julio de 2026

## 1. Estrategia elegida: Blue-Green

Se eligio Blue-Green porque esta aplicacion permite identificar la version activa con
`/version` (`version`, `color` y `hostname`) y Kubernetes puede realizar el corte de
trafico usando unicamente dos `Deployment` y el selector de un `Service`. BLUE conserva
`v1` mientras GREEN se valida con `v2`; cuando GREEN esta listo, el cambio
`slot=blue` a `slot=green` es inmediato. Si el smoke test falla, el rollback consiste
en devolver el selector a BLUE, que sigue levantado. Para una demostracion de
laboratorio esto es mas determinista y facil de evidenciar que Canary, donde seria
necesario hacer muchas peticiones para observar una proporcion estadistica.

Esta eleccion tiene un costo: ambas versiones consumen recursos al mismo tiempo. Ademas,
la base JSON local hace que cada pod tenga un catalogo independiente. En produccion no
usariamos Blue-Green con este almacenamiento; moveriamos el catalogo a una base de datos
externa o a un diseno de persistencia compartida antes de cortar trafico.

## 2. Observacion sobre la persistencia

`DB_PATH=/app/data/products.json` apunta a un volumen `emptyDir`. Ese volumen vive solo
mientras vive el pod. Por eso, al crear un producto y luego eliminar ese pod, el
`Deployment` crea otro pod con un `emptyDir` nuevo y la aplicacion vuelve a cargar los
tres productos semilla. El producto agregado desaparece. Con dos replicas tambien
pueden observarse catalogos distintos segun el pod que atienda cada peticion. Es el
comportamiento esperado de la arquitectura solicitada, no un error a corregir en esta
practica.

## 3. Metricas DORA propias

Los tiempos se calcularon con timestamps ISO-8601 conservados en Git y con el momento
en que cada cambio quedo disponible en el cluster:

| Cambio | Commit | Disponible en el cluster | Lead time |
|---|---|---|---:|
| Runtime distroless `285e565` | 2026-07-23 18:57:46 -05:00 | 2026-07-25 21:34:57.195746 -05:00 | 50 h 37 min 11.196 s |
| Arranque lento `a07b964` | 2026-07-26 00:44:14 -05:00 | 2026-07-26 01:09:59.642816 -05:00 | 25 min 45.643 s |

- **Lead time promedio:** `(50.6198 h + 0.4293 h) / 2 = 25.5246 h`.
- **Frecuencia de despliegue:** `3 promociones exitosas / 2 dias calendario = 1.5 por dia`.
- **Change failure rate simplificado:** `1 despliegue que requirio correccion / 4 intentos = 25 %`.

Para la frecuencia se contabilizaron tres promociones: la v1 estable, la v2 mediante
RollingUpdate y la v2 GREEN preparada y promovida dentro de la estrategia Blue-Green.
Para CFR se considero tambien el despliegue inicial que alcanzo el progress deadline y
requirio corregir permisos del volumen. No se contaron como fallos el error de quoting
de PowerShell, el HTTP 503 intencional de readiness ni el rollback BLUE-GREEN usado como
demostracion controlada.

Frente a la tabla clasica vista en clase, el laboratorio muestra cambios relativamente
frecuentes, pero el lead time promedio queda influido por el primer cambio, que espero
mas de dos dias antes de quedar desplegado. El 25 % de fallos indica que todavia hay
margen para mejorar estabilidad y automatizacion. La muestra es pequena y describe esta
practica, no el rendimiento sostenido de un equipo en produccion.

## 4. Problemas reales y solucion

1. **Vulnerabilidades criticas en la imagen inicial.** Trivy hizo fallar el pipeline
   antes de publicar. Se cambio el runtime final a distroless y el siguiente run termino
   correctamente.
2. **Permisos con usuario no root.** La imagen distroless usa UID/GID 65532 y no podia
   escribir el JSON en el volumen. Se agregaron `runAsUser`, `runAsGroup` y `fsGroup`
   65532, manteniendo `readOnlyRootFilesystem` y el volumen escribible solo en
   `/app/data`.
3. **Readiness durante el arranque lento.** `/health` devuelve 503 durante 12 segundos.
   El readiness tolera ese periodo y la liveness comienza despues. Aumentar replicas no
   resolveria una sonda mal configurada: solo crearia mas pods todavia no listos.
4. **Cambio de trafico y validacion.** El primer intento con `kubectl patch` tuvo un
   problema de quoting en PowerShell. Se reemplazo por `kubectl set selector` y Jordy
   automatizo el corte y rollback con validacion de `EndpointSlice` y smoke tests.
5. **Revalidacion final.** El 28 de julio se arranco nuevamente Minikube sobre Docker,
   se verificaron BLUE y GREEN, se ejecuto el corte real a GREEN, smoke test v2/green,
   rollback a BLUE, smoke test v1/blue y un rollout exitoso del Deployment base con
   `maxUnavailable: 1`, `maxSurge: 1` y `progressDeadlineSeconds: 300`.

## 5. Conclusion

El pipeline aplica fail-fast: las pruebas deben pasar, Trivy bloquea vulnerabilidades
`CRITICAL` y solo entonces se publican las etiquetas SHA y `latest` en GHCR. Kubernetes
aporta RollingUpdate para el despliegue base y Blue-Green para un corte y rollback
rapidos. La practica tambien demostro que la persistencia local con `emptyDir` no es
adecuada para compartir estado entre pods. Como siguiente mejora se externalizaria la
base de datos y se integraria el smoke test como verificacion automatica posterior al
despliegue.
