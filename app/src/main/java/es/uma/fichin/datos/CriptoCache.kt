package es.uma.fichin.datos

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import es.uma.fichin.modelo.Fichaje
import kotlinx.serialization.json.Json
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/* Cifra el objeto Fichaje completo antes de guardarlo.
mediante updateAAD() asociamos criptográficamente el contenido al identificador
y al propietario. Si alguien intercambia los paquetes cifrados entre registros de
distintos usuarios, el descifrado fallará.
*/

object CriptoCache {

    private const val ALIAS = "clave_cache_fichajes"
    private const val TRANSFORMACION = "AES/GCM/NoPadding"

    @Synchronized
    private fun obtenerClave(): SecretKey {
        val almacen = KeyStore.getInstance("AndroidKeyStore")
        almacen.load(null)

        val existente = almacen.getKey(ALIAS, null) as? SecretKey
        if (existente != null) return existente

        val generador = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            "AndroidKeyStore"
        )

        generador.init(
            KeyGenParameterSpec.Builder(
                ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or
                        KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(
                    KeyProperties.ENCRYPTION_PADDING_NONE
                )
                .setKeySize(256)
                .setUserAuthenticationRequired(false)
                .build()
        )

        return generador.generateKey()
    }

    fun cifrar(fichaje: Fichaje, propietario: String): String {
        val cifrador = Cipher.getInstance(TRANSFORMACION)
        cifrador.init(Cipher.ENCRYPT_MODE, obtenerClave())

        cifrador.updateAAD(
            "${fichaje.id}:$propietario".toByteArray(Charsets.UTF_8)
        )

        val texto = Json.encodeToString(
            Fichaje.serializer(),
            fichaje
        )

        val cifrado = cifrador.doFinal(
            texto.toByteArray(Charsets.UTF_8)
        )

        return Base64.encodeToString(cifrador.iv, Base64.NO_WRAP) +
                ":" +
                Base64.encodeToString(cifrado, Base64.NO_WRAP)
    }

    fun descifrar(
        id: Int,
        propietario: String,
        paquete: String
    ): Fichaje {
        val partes = paquete.split(":", limit = 2)
        require(partes.size == 2)

        val nonce = Base64.decode(partes[0], Base64.NO_WRAP)
        val cifrado = Base64.decode(partes[1], Base64.NO_WRAP)

        val cifrador = Cipher.getInstance(TRANSFORMACION)

        cifrador.init(
            Cipher.DECRYPT_MODE,
            obtenerClave(),
            GCMParameterSpec(128, nonce)
        )

        cifrador.updateAAD(
            "$id:$propietario".toByteArray(Charsets.UTF_8)
        )

        val texto = String(
            cifrador.doFinal(cifrado),
            Charsets.UTF_8
        )

        return Json.decodeFromString(
            Fichaje.serializer(),
            texto
        )
    }
}