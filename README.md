# app-FichIN
FichIN es una aplicación de fichaje laboral que permite a un empleado autenticarse y registrar sus entradas y salidas del puesto de trabajo. Cada fichaje almacena la fecha y hora, el tipo de registro y la ubicación del dispositivo en el momento de realizarlo. El usuario puede consultar posteriormente su historial de fichajes y los registros pueden sincronizarse con un servicio remoto.

Consideramos como dato más sensible la ubicación asociada a las horas de entrada y salida del empleado, ya que permite conocer dónde se encontraba una persona en momentos concretos y puede revelar patrones de comportamiento y horarios laborales.

## Equipo
Grupo B

### Miembros
- Javier Gómez Barrios
- Julia Hernández Palma
- María Victoria Pedemonte
- Noelia Mate Ocón
- Francisco Enea

## Dominio
Fichaje laboral con ubicación

## Convenciones

Package name:
es.uma.fichin

minSdk:
26

targetSdk:
37

Justificación de targetSdk:
Se utiliza targetSdk 37 para que la aplicación quede sujeta a los
comportamientos y restricciones de seguridad actuales de Android.

## Requisitos mínimos

| Requisito | Implementación | Responsables |
|---|---|---|
| *Autenticación* | Inicio de sesión del empleado antes de acceder a sus fichajes. | Javier Gómez Barrios |
| *Almacenamiento local sensible* | Historial de fichajes con fecha, hora, tipo y ubicación. | Julia Hernández Palma |
| *API remota* | Sincronización/consulta de fichajes mediante un servicio remoto. | Victoria Pedemonte |
| *Permiso peligroso* | Ubicación solicitada en el momento de realizar el fichaje. | Noelia Mate, Francisco Enea |

## Ramas y revisión:
- main: rama estable.
- feature/*: desarrollo de funcionalidades.
- Integración mediante Pull Request.
- Cada Pull Request debe ser revisado por otro miembro.

## Estado actual del proyecto

La versión actual de FichIN consolida el trabajo realizado en las prácticas P2.2 y P2.3 del Bloque II, con autenticación de usuarios, consulta de fichajes mediante una API remota, persistencia local con Room, listado y pantalla de detalle de los fichajes, acceso a la pantalla de detalle mediante el deep link `fichin://detalle/{id}`, gestión de sesión y limpieza de los datos locales al cerrar sesión, solicitud en tiempo de ejecución del permiso de ubicación.

En el Bloque III se han añadido:

- **P3.1 – Datos en reposo:** almacenamiento local cifrado con AES-GCM y clave en el almacén de claves de Android, protegida con autenticación biométrica.
- **P3.2 – Datos en tránsito:** tráfico en claro prohibido, backend servido por HTTPS y anclaje de la clave pública del servidor. Las excepciones del laboratorio solo existen en la variante de depuración (ver el apartado «Seguridad en tránsito»).

El modelo principal de la aplicación se ha adaptado al dominio mediante la clase `Fichaje`. El backend común de la asignatura conserva los endpoints `/api/elementos`, por lo que esos nombres se mantienen en la comunicación con el servidor.

## Ejecución del proyecto

Desde P3.2 la aplicación se comunica con el backend **solo por HTTPS** y ya **no se usa `adb reverse`**. Cada miembro tiene que preparar su entorno una vez, siguiendo estos pasos.

### 1. Averiguar la IP del ordenador

```bash
ipconfig | findstr /i "IPv4"      # Windows
hostname -I                       # Linux
ipconfig getifaddr en0            # macOS
```

Usad la IP de la red local real. Las que terminan en `.1` suelen ser de WSL, VirtualBox o VMware. Si la IP cambia, hay que repetir los pasos 2 y 4.

### 2. Generar los certificados del backend

En la carpeta `backend` del material común, con la versión de `generar_certificado.sh` del material de P3.2. Se ejecuta en Git Bash, WSL, Linux o macOS, **no en PowerShell**:

```bash
EXTRA=TU_IP ./generar_certificado.sh
```

Genera `ca.pem` (autoridad del laboratorio), `cert.pem` (certificado del servidor), `cert_reserva.pem` (certificado de reserva) y `clave.pem`, e imprime los dos resúmenes SHA-256 de clave pública (actual y reserva).

> `clave.pem` es la clave privada del servidor: **nunca se sube al repositorio**.

### 3. Arrancar el backend en modo TLS

Desde la carpeta `backend`:

```powershell
# Windows (PowerShell)
$env:PUERTO=8443; $env:CERT="cert.pem"; $env:CLAVE="clave.pem"; py servidor.py
```

```bash
# macOS / Linux
PUERTO=8443 CERT=cert.pem CLAVE=clave.pem python3 servidor.py
```

Comprobación: `curl --cacert cert.pem https://TU_IP:8443/api/salud` (en Windows, `curl.exe`).

### 4. Adaptar la aplicación a vuestro entorno

El repositorio lleva los valores de la persona que hizo la integración. Cada miembro tiene que cambiar en local:

| Fichero | Qué cambiar |
| --- | --- |
| `app/src/main/java/es/uma/fichin/datos/ApiServicio.kt` | `BASE_URL = "https://TU_IP:8443/"` |
| `app/src/main/res/xml/network_security_config.xml` | La IP en `<domain>` y los dos `<pin>` |
| `app/src/debug/res/xml/network_security_config.xml` | Lo mismo que el anterior |
| `app/src/debug/res/raw/cert_laboratorio.pem` | Sustituirlo por vuestro `ca.pem` |

Estos cambios son de vuestro entorno: **no los subáis** en vuestros commits.

### 5. Ejecutar FichIN

1. Iniciar el emulador.
2. Comprobar que no queda ni proxy ni reenvío de puertos de prácticas anteriores:
   ```bash
   adb reverse --remove-all
   adb shell settings put global http_proxy :0
   ```
3. Ejecutar la variante **debug** desde Android Studio.

## Seguridad en tránsito

| Elemento | Dónde | Qué hace |
| --- | --- | --- |
| Tráfico en claro prohibido | `src/main/res/xml/network_security_config.xml` (`base-config`) | Ninguna conexión HTTP sin cifrar, tampoco de bibliotecas de terceros |
| Anclaje de certificados | Mismo fichero (`domain-config` + `pin-set`) | Solo se acepta la clave pública del servidor actual o la de reserva. Caduca el **2026-12-31** |
| Excepciones del laboratorio | `src/debug/res/xml/network_security_config.xml` (`debug-overrides`) y `src/debug/res/raw/cert_laboratorio.pem` | CA del laboratorio y almacén del usuario. **Solo en debug** |

- La variante **release** no contiene el certificado del laboratorio ni el bloque `debug-overrides`. Se ha comprobado con *Analyze APK*.
- En **debug**, `debug-overrides` desactiva el anclaje para las cadenas que terminan en esas anclas. Por eso un proxy puede interceptar mientras se depura. Es lo esperado.
- La release no confía en la CA del laboratorio, así que contra el backend del laboratorio no conecta. En producción el servidor tendría un certificado de una CA pública.
- **Antes del 2026-12-31**, o si se regeneran los certificados, hay que actualizar los pins y la caducidad siguiendo el procedimiento de rotación del documento de diseño.

**Pendiente conocido:** la variante release se cierra al arrancar (`IllegalAccessError`) por la configuración de optimización R8 (`packageScope` en `app/build.gradle.kts`). No está relacionado con la configuración de red.

## Usuarios de prueba

El backend común proporciona, entre otros, los siguientes usuarios de prueba:

| Usuario | Contraseña |
| --- | --- |
| `ana` | `Practica2024` |
| `luis` | `Practica2024` |


## Reconocimiento de una aplicación real: Bixpe (com.bixpe.chronos v3.2.74)
Se ha analizado **Bixpe Chronos**, una aplicación de control horario
perteneciente al mismo dominio que nuestro proyecto de fichaje laboral.

Paquete analizado: `com.bixpe.chronos`

| Qué mirar | Herramienta | Observación |
|---|---|---|
| Permisos declarados | `aapt2 dump permissions` | Se observan 20 permisos. Entre ellos aparecen permisos sensibles relacionados con ubicación (`ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`), cámara, cuentas (`GET_ACCOUNTS`) y notificaciones. También declara permisos heredados de almacenamiento (`READ_EXTERNAL_STORAGE`, `WRITE_EXTERNAL_STORAGE`) y permisos relacionados con publicidad y atribución (`AD_ID`, `ACCESS_ADSERVICES_AD_ID`, `ACCESS_ADSERVICES_ATTRIBUTION`, `BIND_GET_INSTALL_REFERRER_SERVICE`). La ubicación resulta coherente con la funcionalidad de fichaje; otros permisos, como cuentas o los relacionados con publicidad y atribución, no se justifican directamente a partir de la funcionalidad principal observada y merecen revisión. No se observa permiso de ubicación en segundo plano. |
| Componentes exportados | `apktool` + lectura de `AndroidManifest.xml` | Se encontraron **4 componentes con `android:exported="true"`**: `MainActivity`, un `FirebaseService` y dos `BroadcastReceiver`. `MainActivity` debe ser accesible para actuar como entrada de la aplicación. Los receivers están protegidos por permisos (`android.permission.DUMP` y `com.google.android.c2dm.permission.SEND`). `FirebaseService` aparece exportado sin un `android:permission` asociado en su declaración, por lo que merece una revisión adicional. |
| Esquemas de firma | `apksigner verify --print-certs` | Verifica mediante los esquemas **v1, v2 y v3**; v3.1 y v4 no aparecen verificados. Tiene un único firmante: `CN=Abbanza, OU=Abbanza, O=Abbanza, L=Madrid, ST=Madrid, C=34`. Utiliza una clave RSA de **1024 bits**. |
| minSdk y targetSdk | `aapt2 dump badging` | Versión **3.2.74** (`versionCode 531`), `minSdkVersion=23` (Android 6.0) y `targetSdkVersion=35` (Android 15). El target se encuentra dos niveles de API por debajo de la plataforma API 37 utilizada actualmente en nuestro entorno de prácticas. |
| Número de piezas instaladas | `adb shell pm path` | El comando devuelve una única ruta, correspondiente a `base.apk`, por lo que en el dispositivo analizado la aplicación está instalada como **una sola pieza**, sin split APKs visibles. |



### Observaciones del reconocimiento

- **¿Pide algún permiso que no sabríamos justificar?**  
  Sí. Aunque la ubicación es coherente con una aplicación de fichaje, permisos como
  `GET_ACCOUNTS` y los relacionados con publicidad y atribución no se justifican
  directamente a partir de la funcionalidad principal observada y requerirían una
  justificación adicional.

- **¿Cuántos componentes tiene exportados?**  
  Se han identificado **4 componentes exportados**. `FirebaseService` merece una
  revisión adicional porque aparece exportado sin un permiso asociado en su declaración.
