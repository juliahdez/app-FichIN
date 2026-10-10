# app-FichIN
FichIN es una aplicación de fichaje laboral que permite a un empleado autenticarse y registrar sus entradas y salidas del puesto de trabajo. Cada fichaje almacena la fecha y hora, el tipo de registro y la ubicación del dispositivo en el momento de realizarlo. El usuario puede consultar posteriormente su historial de fichajes y los registros pueden sincronizarse con un servicio remoto.

Consideramos como dato más sensible la ubicación asociada a las horas de entrada y salida del empleado, ya que permite conocer dónde se encontraba una persona en momentos concretos y puede revelar patrones de comportamiento y horarios laborales.


## Equipo
Grupo B

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
| *Permiso peligroso* | Ubicación solicitada en el momento de realizar el fichaje. | Noelia Mate , Francisco Enea |

## Ramas y revisión:
- main: rama estable.
- feature/*: desarrollo de funcionalidades.
- Integración mediante Pull Request.
- Cada Pull Request debe ser revisado por otro miembro.


