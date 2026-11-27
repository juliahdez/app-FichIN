package es.uma.fichin.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import es.uma.fichin.modelo.*
import androidx.compose.foundation.clickable
import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat

/**
 * Listado de elementos. ESTÁ TERMINADA: no hace falta tocarla en P2.2.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PantallaLista(
    estado: EstadoUi<List<Fichaje>>,
    onRecargar: () -> Unit,
    onSalir: () -> Unit,
    onAbrir: (Int) -> Unit
) {
    val contexto = LocalContext.current
    var concedido by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(contexto, Manifest.permission.ACCESS_FINE_LOCATION) ==
                    PackageManager.PERMISSION_GRANTED ||
                    ContextCompat.checkSelfPermission(
                        contexto,
                        Manifest.permission.ACCESS_COARSE_LOCATION
                    ) ==
                    PackageManager.PERMISSION_GRANTED
        )
    }
    val lanzador = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { resultado ->
        concedido = resultado.values.any { it }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("FichIN") },
                actions = {
                    TextButton(onClick = onRecargar) {
                        Text("Actualizar")
                    }
                    TextButton(onClick = onSalir) {
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

            // Estado de la jornada y preparación de ubicación
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

                    Spacer(Modifier.height(8.dp))

                    Text(
                        if (concedido)
                            "La ubicación está disponible para registrar un fichaje."
                        else
                            "Para registrar un fichaje será necesario permitir el acceso a la ubicación.",
                        style = MaterialTheme.typography.bodyMedium
                    )

                    Spacer(Modifier.height(12.dp))

                    if (!concedido) {
                        Button(
                            onClick = {
                                lanzador.launch(
                                    arrayOf(
                                        Manifest.permission.ACCESS_FINE_LOCATION,
                                        Manifest.permission.ACCESS_COARSE_LOCATION
                                    )
                                )
                            }
                        ) {
                            Text("Activar ubicación")
                        }
                    } else {
                        Text(
                            "✓ Ubicación preparada",
                            style = MaterialTheme.typography.labelLarge
                        )
                    }
                }
            }

            Text(
                "Historial de fichajes",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(
                    start = 16.dp,
                    end = 16.dp,
                    bottom = 8.dp
                )
            )

            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                when (estado) {

                    is EstadoUi.Reposo ->
                        Text("Pulsa Actualizar para cargar los fichajes")

                    is EstadoUi.Cargando ->
                        CircularProgressIndicator()

                    is EstadoUi.Error ->
                        Text("No se han podido cargar los fichajes")

                    is EstadoUi.Exito ->
                        LazyColumn(
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(horizontal = 16.dp)
                        ) {
                            items(estado.datos) { fichaje ->

                                Card(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 6.dp)
                                        .clickable {
                                            onAbrir(fichaje.id)
                                        }
                                ) {
                                    Column(
                                        modifier = Modifier.padding(16.dp)
                                    ) {
                                        Text(
                                            fichaje.titulo,
                                            style = MaterialTheme.typography.titleMedium
                                        )

                                        Spacer(Modifier.height(4.dp))

                                        Text(
                                            fichaje.contenido,
                                            style = MaterialTheme.typography.bodyMedium
                                        )

                                        Spacer(Modifier.height(6.dp))

                                        Text(
                                            fichaje.fecha,
                                            style = MaterialTheme.typography.labelSmall
                                        )
                                    }
                                }
                            }
                        }
                }
            }
        }
    }}