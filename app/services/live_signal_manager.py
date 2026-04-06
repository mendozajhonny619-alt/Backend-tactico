from datetime import datetime

class LiveSignalManager:

    active_signals = []

    @staticmethod
    def actualizar_signales(nuevas_senales):
        ahora = datetime.now()

        # 1. Eliminar señales viejas (más de 15 min)
        señales_actualizadas = []
        for s in LiveSignalManager.active_signals:
            tiempo = (ahora - s["created_at"]).seconds / 60
            if tiempo <= 15:
                señales_actualizadas.append(s)

        LiveSignalManager.active_signals = señales_actualizadas

        # 2. Agregar nuevas señales (evitar duplicados exactos)
        for nueva in nuevas_senales:
            match_id = nueva["match"].get("match_id")

            existe = any(
                s["match"].get("match_id") == match_id
                for s in LiveSignalManager.active_signals
            )

            if not existe:
                nueva["created_at"] = ahora
                LiveSignalManager.active_signals.append(nueva)

        # 3. Ordenar por signal_score
        LiveSignalManager.active_signals.sort(
            key=lambda x: x["match"].get("signal_score", 0),
            reverse=True
        )

        # 4. Máximo 6 señales
        LiveSignalManager.active_signals = LiveSignalManager.active_signals[:6]

        return LiveSignalManager.active_signals
