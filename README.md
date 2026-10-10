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

| Requisito | Implementación prevista | Responsables |
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
