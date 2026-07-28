# Informe de reflexion - Practica CI/CD

**Integrantes:** Gabriel Alexander Cordova Solorzano y Jordy Espinoza  
**Repositorio:** <https://github.com/UPSGabriel/inventario-app-cicd-final>  
**Fecha de corte:** 26 de julio de 2026

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

Los tiempos se calcularon con timestamps ISO-8601 conservados en Git y en el registro de
despliegue:

| Cambio | Commit | Disponible en el cluster | Lead time |
|---|---|---|---:|
| Runtime distroless `285e565` | 2026-07-23 18:57:46 -05:00 | 2026-07-25 21:34:57.195746 -05:00 | 50 h 37 min 11.196 s |
| Arranque lento `a07b964` | 2026-07-26 00:44:14 -05:00 | 2026-07-26 01:09:59.642816 -05:00 | 25 min 45.643 s |

- **Lead time promedio:** `(50.6198 h + 0.4293 h) / 2 = 25.5246 h`.
- **Frecuencia de despliegue:** `2 promociones exitosas / 2 dias calendario = 1 por dia`.
- **Change failure rate simplificado:** `1 intento que requirio correccion / 3 intentos
  registrados = 33.3 %`.

El denominador del change failure rate incluye el rollout que alcanzo su
`progressDeadlineSeconds` y requirio corregir permisos del volumen, mas los dos
despliegues exitosos con timestamp. Los cambios del selector Blue-Green no se cuentan
como nuevos despliegues de aplicacion porque no cambian la imagen: solo enrutan trafico
entre Deployments ya disponibles.

Frente a la tabla clasica vista en clase, la frecuencia de una vez por dia y el lead
time promedio cercano a un dia muestran un flujo rapido para un laboratorio. El 33.3 %
de fallos indica que la estabilidad todavia debe mejorar. La muestra es pequena, por lo
que estos valores describen esta practica y no el rendimiento sostenido de un equipo.

## 4. Problemas reales y solucion

1. **Vulnerabilidades criticas en la imagen inicial.** Trivy hizo fallar el run
   `29980646258`. Se cambio el runtime final a distroless y el run de `285e565`
   (`30054762604`) termino correctamente antes de publicar.
2. **Permisos con usuario no root.** La imagen distroless usa UID/GID 65532 y no podia
   escribir el JSON en el volumen. Se agregaron `runAsUser`, `runAsGroup` y `fsGroup`
   65532, manteniendo `readOnlyRootFilesystem` y el volumen escribible solo en
   `/app/data`.
3. **Readiness durante el arranque lento.** `/health` devuelve 503 durante 12 segundos.
   El readiness tolera ese periodo y la liveness comienza despues. Aumentar replicas no
   resolveria una sonda mal configurada: solo crearia mas pods todavia no listos.
4. **Reproduccion y cambio de trafico.** Se corrigio el orden del README para crear el
   Secret antes del Deployment y se agregaron scripts que validan el Deployment,
   cambian el selector, verifican los endpoints y ejecutan smoke tests.

## 5. Conclusion

El pipeline aplica fail-fast: las pruebas deben pasar, Trivy bloquea vulnerabilidades
`CRITICAL` y solo entonces se publican las etiquetas SHA y `latest` en GHCR. Kubernetes
aporta RollingUpdate para el despliegue base y Blue-Green para un corte y rollback
rapidos. La principal deuda tecnica es la persistencia local; una siguiente iteracion
deberia externalizar la base de datos y ejecutar automaticamente el smoke test despues
del despliegue.

