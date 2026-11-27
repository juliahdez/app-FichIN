package es.uma.fichin.ui

import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException
import java.util.Locale

fun formatearFechaFichaje(fecha: String): String {
    return try {
        val instante = Instant.parse(fecha)

        val formato = DateTimeFormatter
            .ofPattern("dd/MM/yyyy ' ' HH:mm", Locale.forLanguageTag("es-ES"))
            .withZone(ZoneId.systemDefault())

        formato.format(instante)

    } catch (e: DateTimeParseException) {
        fecha
    }
}