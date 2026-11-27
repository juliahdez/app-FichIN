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

FichIN permite a los empleados autenticarse, registrar entradas y salidas de su jornada laboral utilizando la ubicación del dispositivo y consultar su historial de fichajes.

Los fichajes se almacenan de forma persistente en una base de datos SQLite del servidor. La aplicación mantiene una copia local cifrada mediante Room para permitir la consulta del historial sin conexión.

### Funcionalidades implementadas

- Inicio y cierre de sesión.
- Protección biométrica de la sesión.
- Identificación del empleado autenticado.
- Registro de entradas y salidas con ubicación.
- Solicitud del permiso de ubicación únicamente al fichar.
- Consulta del estado de la jornada laboral.
- Historial y detalle de fichajes.
- Persistencia remota y caché local cifrada.

## Medidas de seguridad implementadas

### Aplicación Android

- Cifrado AES-GCM de la sesión mediante Android Keystore y autenticación biométrica.
- Cifrado AES-GCM del historial local mediante una clave independiente en Android Keystore.
- Asociación criptográfica de cada registro cifrado con su identificador y propietario mediante AAD.
- Eliminación de la caché del usuario al cerrar sesión.
- Gestión de sesiones caducadas y revocación remota del token al cerrar sesión con conexión.
- Prohibición del tráfico HTTP.
- Anclaje de claves públicas y separación de las excepciones TLS de depuración y publicación.
- Protección de capturas de pantalla mediante FLAG_SECURE.
- Reducción de la información sensible en los registros de depuración.

### Backend

- HTTPS obligatorio, con TLS 1.2 como versión mínima.
- Contraseñas protegidas mediante PBKDF2-HMAC-SHA256 y sal individual.
- Tokens aleatorios, almacenados mediante su resumen criptográfico, con caducidad y revocación.
- Limitación de intentos de autenticación.
- Autorización de lectura y escritura basada en el usuario autenticado.
- Validación de peticiones y coordenadas.
- Fecha y hora del fichaje determinadas por el servidor.
- Consultas SQL parametrizadas.
- Transacciones para controlar registros simultáneos de entrada y salida.
- Eliminación de endpoints administrativos y datos personales innecesarios.

## Backend propio

El directorio `backend/` contiene:

| Archivo | Función |
|---|---|
| `servidor.py` | API REST de FichIN |
| `generar_certificado.sh` | Generación de certificados TLS |
| `probar_backend.py` | Pruebas automáticas de seguridad |

La base de datos `fichin.db` se genera automáticamente. No se incluyen en el repositorio las bases de datos locales ni las claves privadas de los certificados.

Se requiere Python 3 y OpenSSL para preparar el entorno.

## Ejecución en desarrollo

### 1. Clonar el repositorio y abrirlo en Android Studio

### 2. Obtener la IP local del ordenador

```bash
ipconfig                        # Windows
hostname -I                     # Linux
ipconfig getifaddr en0          # macOS
```

### 3. Generar los certificados TLS

Desde el directorio `backend`, utilizando Git Bash en Windows o la terminal en macOS/Linux:

```bash
EXTRA=TU_IP bash generar_certificado.sh
```

Guardar los dos resúmenes SHA-256 generados para configurar el anclaje.

Las claves privadas y los certificados generados localmente no deben subirse al repositorio.

### 4. Arrancar el backend

**Windows (PowerShell):**

```powershell
$env:PUERTO="8443"
$env:CERT="cert.pem"
$env:CLAVE="clave.pem"
py servidor.py
```

**macOS / Linux:**

```bash
PUERTO=8443 CERT=cert.pem CLAVE=clave.pem python3 servidor.py
```

El servidor requiere HTTPS obligatoriamente.

### 5. Comprobar la disponibilidad

**Windows:**

```powershell
curl.exe --cacert ca.pem https://TU_IP:8443/api/salud
```

**macOS / Linux:**

```bash
curl --cacert ca.pem https://TU_IP:8443/api/salud
```

### 6. Adaptar la configuración local de Android

| Archivo | Modificación |
|---|---|
| `app/src/main/java/es/uma/fichin/datos/ApiServicio.kt` | BASE_URL con la IP del ordenador y puerto 8443 |
| `app/src/debug/res/xml/network_security_config.xml` | IP y resúmenes de las claves públicas |
| `app/src/debug/res/raw/cert_laboratorio.pem` | Sustituir por el ca.pem generado |

Estos cambios son específicos del entorno de desarrollo y no deben incorporarse a los commits.

### 7. Preparar el emulador

Eliminar posibles configuraciones de prácticas anteriores:

```bash
adb reverse --remove-all
adb shell settings put global http_proxy :0
```

### 8. Ejecutar FichIN

Seleccionar la variante debug en Android Studio y ejecutar la aplicación.

## Pruebas del backend

Desde el directorio `backend`:

**Windows:**

```powershell
py probar_backend.py
```

**macOS / Linux:**

```bash
python3 probar_backend.py
```

Las pruebas automáticas verifican los controles de autenticación, autorización, validación de peticiones, gestión de sesiones y persistencia de fichajes.

## Usuarios de prueba

| Usuario | Contraseña |
|---|---|
| ana | Practica2024 |
| luis | Practica2024 |


## Pendientes antes de la entrega del Bloque III

- Completar el endurecimiento correspondiente a P3.3.
- Revisar componentes exportados, enlaces profundos, backups y registros de publicación.
- Revisar las operaciones concurrentes durante el cierre de sesión.
- Resolver la configuración definitiva de dirección, certificados y anclaje para el despliegue del grupo auditor.
- Resolver el error IllegalAccessError de la variante release y verificar la configuración de R8.
- Generar, firmar y comprobar el APK definitivo.
- Calcular el resumen SHA-256.
- Completar el documento de diseño de seguridad y la nota de puesta en marcha.

Las instrucciones actuales corresponden al entorno de desarrollo. La configuración definitiva para el grupo auditor se documentará antes de la entrega.


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
