package es.uma.fichin.ui

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.os.CancellationSignal
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.core.location.LocationManagerCompat
import es.uma.fichin.modelo.*
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.coroutines.resume
import androidx.compose.ui.graphics.Color

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PantallaLista(
    estado: EstadoUi<List<Fichaje>>,
    estadoRegistro: EstadoUi<Fichaje>,
    onRecargar: () -> Unit,
    onSalir: () -> Unit,
    onAbrir: (Int) -> Unit,
    onFichar: (String, Double, Double) -> Unit,
    nombreEmpleado: String?,
    onCargarPerfil: () -> Unit,
) {
    val contexto = LocalContext.current
    val scope = rememberCoroutineScope()

    var obteniendoUbicacion by remember {
        mutableStateOf(false)
    }

    var tipoPendiente by remember {
        mutableStateOf<String?>(null)
    }

    var mensaje by remember {
        mutableStateOf<String?>(null)
    }

    // El estado de la jornada se obtiene del historial.
    val ultimo = if (estado is EstadoUi.Exito) {
        estado.datos.maxByOrNull { it.id }
    } else {
        null
    }

    val enJornada = ultimo?.titulo == "Entrada"
    val tipoSiguiente = if (enJornada) "Salida" else "Entrada"

    val ocupado = obteniendoUbicacion ||
            tipoPendiente != null ||
            estadoRegistro is EstadoUi.Cargando

    // Obtiene la ubicación antes de enviar el fichaje.
    fun ficharConUbicacion(tipo: String) {
        if (obteniendoUbicacion) return

        obteniendoUbicacion = true
        mensaje = null

        scope.launch {
            try {
                val ubicacion = obtenerUbicacionActual(contexto)

                if (ubicacion == null) {
                    mensaje = "No se ha podido obtener la ubicación. Comprueba que esté activada."
                } else {
                    onFichar(
                        tipo,
                        ubicacion.latitude,
                        ubicacion.longitude
                    )
                }
            } catch (e: SecurityException) {
                mensaje = "No hay permiso para acceder a la ubicación."
            } catch (e: IllegalArgumentException) {
                mensaje = "Ubicación no disponible."
            } finally {
                obteniendoUbicacion = false
            }
        }
    }

    // Solicitud del permiso únicamente al intentar fichar.
    val lanzador = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { resultado ->
        val tipo = tipoPendiente
        tipoPendiente = null

        if (resultado.values.any { it } && tipo != null) {
            ficharConUbicacion(tipo)
        } else {
            mensaje = "Necesitas conceder acceso a la ubicación para fichar."
        }
    }

    // Cargar el historial automáticamente al entrar.
    LaunchedEffect(Unit) {
        onRecargar()
        onCargarPerfil()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("FichIN") },
                actions = {
                    TextButton(
                        onClick = onRecargar,
                        enabled = !ocupado
                    ) {
                        Text("Actualizar")
                    }

                    TextButton(
                        onClick = onSalir,
                        enabled = !ocupado
                    ) {
                        Text("Salir")
                    }
                }
            )
        }
    ) { relleno ->

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(relleno)
        ) {

            if (!nombreEmpleado.isNullOrBlank()) {
                Text(
                    text = "Hola, $nombreEmpleado",
                    style = MaterialTheme.typography.headlineSmall,
                    modifier = Modifier.padding(
                        start = 16.dp,
                        end = 16.dp,
                        top = 12.dp
                    )
                )
            }

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        "Jornada laboral",
                        style = MaterialTheme.typography.titleLarge
                    )

                    Spacer(Modifier.height(12.dp))

                    Text(
                        text = when {
                            estado !is EstadoUi.Exito ->
                                "Consultando jornada..."

                            enJornada -> "EN JORNADA"

                            else -> "FUERA DE JORNADA"
                        },
                        color = if (enJornada)
                            Color(0xFF2E7D32)
                        else
                            MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.titleMedium
                    )

                    if (enJornada && ultimo != null) {
                        Spacer(Modifier.height(6.dp))
                        Text(
                            "Última entrada: ${formatearFechaFichaje(ultimo.fecha)}"
                        )
                    }

                    Spacer(Modifier.height(16.dp))

                    Button(
                        enabled = !ocupado && estado is EstadoUi.Exito,
                        modifier = Modifier.fillMaxWidth(),
                        onClick = {
                            mensaje = null

                            if (tienePermisoUbicacion(contexto)) {
                                ficharConUbicacion(tipoSiguiente)
                            } else {
                                tipoPendiente = tipoSiguiente

                                lanzador.launch(
                                    arrayOf(
                                        Manifest.permission.ACCESS_FINE_LOCATION,
                                        Manifest.permission.ACCESS_COARSE_LOCATION
                                    )
                                )
                            }
                        }
                    ) {
                        Text(
                            when {
                                obteniendoUbicacion ->
                                    "Obteniendo ubicación..."

                                estadoRegistro is EstadoUi.Cargando ->
                                    "Registrando..."

                                enJornada -> "Fichar salida"

                                else -> "Fichar entrada"
                            }
                        )
                    }

                    Spacer(Modifier.height(8.dp))

                    Text(
                        "La ubicación se solicita únicamente al fichar.",
                        style = MaterialTheme.typography.bodySmall
                    )

                    if (mensaje != null) {
                        Spacer(Modifier.height(8.dp))
                        Text(
                            mensaje.orEmpty(),
                            color = MaterialTheme.colorScheme.error
                        )
                    } else if (!ocupado) {
                        when (estadoRegistro) {
                            is EstadoUi.Exito -> Text(
                                "Fichaje registrado correctamente."
                            )

                            is EstadoUi.Error -> Text(
                                "No se ha podido registrar el fichaje. Actualiza e inténtalo de nuevo.",
                                color = MaterialTheme.colorScheme.error
                            )

                            else -> Unit
                        }
                    }
                }
            }

            Text(
                "Historial de fichajes",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(
                    start = 16.dp,
                    bottom = 8.dp
                )
            )

            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
                contentAlignment = Alignment.Center
            ) {
                when (estado) {
                    is EstadoUi.Reposo,
                    is EstadoUi.Cargando ->
                        CircularProgressIndicator()

                    is EstadoUi.Error ->
                        Text("No se han podido cargar los fichajes.")

                    is EstadoUi.Exito -> {
                        if (estado.datos.isEmpty()) {
                            Text("Todavía no tienes fichajes.")
                        } else {
                            LazyColumn(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(horizontal = 16.dp)
                            ) {
                                items(
                                    estado.datos.sortedByDescending { it.id }
                                ) { fichaje ->

                                    Card(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(vertical = 6.dp)
                                            .clickable(enabled = !ocupado) {
                                                onAbrir(fichaje.id)
                                            }
                                    ) {
                                        Column(
                                            Modifier.padding(16.dp)
                                        ) {
                                            Text(
                                                fichaje.titulo,
                                                style = MaterialTheme.typography.titleMedium
                                            )

                                            Spacer(Modifier.height(4.dp))

                                            Text(
                                                if (fichaje.contenido.startsWith("Latitud:", ignoreCase = true))
                                                    "Ubicación registrada"
                                                else
                                                    fichaje.contenido,
                                                style = MaterialTheme.typography.bodyMedium
                                            )

                                            Spacer(Modifier.height(6.dp))

                                            Text(
                                                formatearFechaFichaje(fichaje.fecha),
                                                style = MaterialTheme.typography.labelMedium
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// Comprueba si Android permite acceder a la ubicación.
private fun tienePermisoUbicacion(contexto: Context): Boolean {
    return ContextCompat.checkSelfPermission(
        contexto,
        Manifest.permission.ACCESS_FINE_LOCATION
    ) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(
                contexto,
                Manifest.permission.ACCESS_COARSE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
}

// Obtiene una ubicación actual, sin rastreo en segundo plano.
@SuppressLint("MissingPermission")
private suspend fun obtenerUbicacionActual(
    contexto: Context
): Location? {

    if (!tienePermisoUbicacion(contexto)) return null

    val gestor = contexto.getSystemService(
        Context.LOCATION_SERVICE
    ) as LocationManager

    val permisoPreciso = ContextCompat.checkSelfPermission(
        contexto,
        Manifest.permission.ACCESS_FINE_LOCATION
    ) == PackageManager.PERMISSION_GRANTED

    val proveedor = when {
        permisoPreciso &&
                gestor.isProviderEnabled(LocationManager.GPS_PROVIDER) ->
            LocationManager.GPS_PROVIDER

        gestor.isProviderEnabled(LocationManager.NETWORK_PROVIDER) ->
            LocationManager.NETWORK_PROVIDER

        else -> return null
    }

    return withTimeoutOrNull(20_000L) {
        suspendCancellableCoroutine<Location?> { continuacion ->

            val cancelacion = CancellationSignal()

            continuacion.invokeOnCancellation {
                cancelacion.cancel()
            }

            LocationManagerCompat.getCurrentLocation(
                gestor,
                proveedor,
                cancelacion,
                ContextCompat.getMainExecutor(contexto)
            ) { ubicacion ->
                if (continuacion.isActive) {
                    continuacion.resume(ubicacion)
                }
            }
        }
    }
}