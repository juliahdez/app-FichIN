package es.uma.fichin.datos

import retrofit2.converter.kotlinx.serialization.asConverterFactory
import es.uma.fichin.modelo.*
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.http.*

/* ==========================================================================
   EL ACCESO AL BACKEND
   Teoría: sesiones 2.5.5 (red), 2.4.5 (corrutinas) y 3.5 (comunicaciones
   seguras).

   Desde P3.2 el backend se sirve SOLO por HTTPS (puerto 8443). La política
   de red está declarada en res/xml/network_security_config.xml: prohíbe el
   tráfico en claro y ancla la clave pública del servidor (pin-set con pin de
   reserva y caducidad). Las excepciones del laboratorio (CA propia y almacén
   del usuario) existen SÓLO en la variante debug, en src/debug/res.
   ========================================================================== */
/**
 * La interfaz describe la API: una función por endpoint. Retrofit genera en
 * tiempo de ejecución la clase que hace las peticiones de verdad, así que aquí
 * no hay ni una línea de código de red.
 *
 * Todas son `suspend`, de modo que sólo pueden llamarse desde una corrutina y
 * nunca bloquean el hilo de la interfaz.
 */
interface ApiServicio {

    /** El cuerpo se serializa a JSON a partir de la clase de datos. */
    @POST("api/login")
    suspend fun login(@Body peticion: PeticionLogin): RespuestaLogin

    /**
     * La cabecera de autorización viaja como parámetro: quien llame tiene que
     * componer el valor "Bearer <token>". Lo hace el Repositorio.
     */
    @GET("api/elementos")
    suspend fun fichajes(@Header("Authorization") autorizacion: String): RespuestaElementos

    @POST("api/elementos")
    suspend fun registrarFichaje(
        @Header("Authorization") autorizacion: String,
        @Body peticion: PeticionFichaje
    ): Fichaje

    @GET("api/elementos/{id}")
    suspend fun fichaje(
        @Header("Authorization") autorizacion: String,
        @Path("id") id: Int
    ): Fichaje

    @GET("api/perfil")
    suspend fun perfil(@Header("Authorization") autorizacion: String): Perfil
}

object ClienteRed {

    /**
     * Dirección del backend, por HTTPS.
     *
     * Es la IP del ordenador en la red local, no 10.0.2.2 ni localhost:
     * tiene que significar lo mismo para el emulador y para el proxy de
     * intercepción de P3.2. Cada miembro pone aquí SU IP, la misma que en
     * <domain> de los dos network_security_config.xml y la que se pasa en
     * EXTRA= al generar los certificados del backend.
     *
     * PARA EL CUADERNO: esta dirección queda escrita en el artefacto y se
     * recupera decompilándolo, tal como comprobaste en la práctica P2.1.
     * ¿Es eso un problema? ¿Y si en lugar de una dirección fuera una clave?
     */
    const val BASE_URL = "https://192.168.1.96:8443/"

    fun crear(): ApiServicio {

        /*
         * El interceptor de registro imprime en logcat cada petición y cada
         * respuesta. Con nivel BODY imprime también el cuerpo, así que en la
         * petición de acceso saldrán el usuario y la contraseña en claro.
         *
         * Es comodísimo mientras se desarrolla y es un desastre si llega a la
         * versión publicada.
         *
         * PARA EL CUADERNO: ¿qué ocurriría si este interceptor se publicase?
         * ¿Quién podría leer esos registros, y con qué privilegios? Se retoma
         * en la sesión 3.6.
         */
        val registro = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }

        /*
         * El cliente HTTP se construye UNA VEZ y lo hereda toda la aplicación.
         * En P3.2 el anclaje de certificados se ha hecho de forma declarativa,
         * en network_security_config.xml, y no en este cliente: la política
         * se aplica a todo el proceso y se audita leyendo un solo fichero.
         */
        val cliente = OkHttpClient.Builder()
            .addInterceptor(registro)
            .build()

        /*
         * ignoreUnknownKeys = true evita que la aplicación se caiga si el
         * servidor añade un campo que nosotros no conocemos. Es tolerancia
         * razonable, y no debe confundirse con validar la respuesta, que es
         * otra cosa y se trata en la sesión 2.5.5.
         */
        val json = Json { ignoreUnknownKeys = true }

        return Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(cliente)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(ApiServicio::class.java)
    }
}
