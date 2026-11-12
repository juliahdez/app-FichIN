package es.uma.fichin

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.compose.setContent
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import es.uma.fichin.datos.*
import es.uma.fichin.ui.Navegacion
import es.uma.fichin.ui.PuertaBiometrica
import es.uma.fichin.ui.theme.FichINTheme

/**
 * Punto de entrada · versión P3.1 (paso 4).
 *
 * Tres cambios respecto a P2.2:
 *  1. FragmentActivity en lugar de ComponentActivity (lo exige BiometricPrompt).
 *  2. La sesión se crea UNA vez y se comparte entre repositorio y puerta.
 *  3. La navegación va envuelta en PuertaBiometrica.
 *
 * Se mantiene el FLAG_SECURE que ya tenía FichIN.
 */
class MainActivity : FragmentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setFlags(
            WindowManager.LayoutParams.FLAG_SECURE,
            WindowManager.LayoutParams.FLAG_SECURE
        )

        // CAMBIO 2: una sola instancia, compartida por el repositorio y la puerta
        val sesion = SesionLocal(applicationContext)

        val repositorio = Repositorio(
            api = ClienteRed.crear(),
            sesion = sesion,
            dao = BaseDatos.obtener(applicationContext).elementoDao()
        )

        setContent {
            FichINTheme {
                val vistaModelo: VistaModelo = viewModel(factory = FabricaVistaModelo(repositorio))

                // CAMBIO 3: la navegación sólo se compone si la sesión está abierta
                PuertaBiometrica(actividad = this@MainActivity, sesion = sesion) {
                    Navegacion(vistaModelo, hayDeSesion = sesion.haySesion())
                }
            }
        }
    }
}

class FabricaVistaModelo(private val repositorio: Repositorio) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        VistaModelo(repositorio) as T
}