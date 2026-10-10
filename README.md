# app-FichIN
FichUMA es una aplicación de fichaje laboral que permite a un empleado autenticarse y registrar sus entradas y salidas del puesto de trabajo. Cada fichaje almacena la fecha y hora, el tipo de registro y la ubicación del dispositivo en el momento de realizarlo. El usuario puede consultar posteriormente su historial de fichajes y los registros pueden sincronizarse con un servicio remoto.

Consideramos como dato más sensible la ubicación asociada a las horas de entrada y salida del empleado, ya que permite conocer dónde se encontraba una persona en momentos concretos y puede revelar patrones de comportamiento y horarios laborales.

Requisitos mínimos

| Requisito | Implementación prevista |
|---|---|
| *Autenticación* | Inicio de sesión del empleado antes de acceder a sus fichajes. |
| *Almacenamiento local sensible* | Historial de fichajes con fecha, hora, tipo y ubicación. |
| *API remota* | Sincronización/consulta de fichajes mediante un servicio remoto. |
| *Permiso peligroso* | Ubicación solicitada en el momento de realizar el fichaje. |
