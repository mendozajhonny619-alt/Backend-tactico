from datetime import datetime

class LiveSignalManager:

    active_signals = []

    @staticmethod
    def actualizar_signales(nuevas_senales, live_matches):
        ahora = datetime.now()

        señales_actualizadas = []

        for s in LiveSignalManager.active_signals:
            match_id = s["match"].get("match_id")
            minuto_creacion = s["match"].get("minute", 0)

            partido_actual = next(
                (m for m in live_matches if m.get("match_id") == match_id),
                None
            )

            if not partido_actual:
                continue

            minuto_actual = partido_actual.get("minute", 0)

            # ⏱️ tiempo desde que se creó
            tiempo = minuto_actual - minuto_creacion

            marcador_antes = s["match"].get("score")
            marcador_actual = partido_actual.get("score")

            # 🎯 DETECTAR GOL
            gol_ocurrio = marcador_antes != marcador_actual

            # 🔥 REGLA DE CIERRE
            if gol_ocurrio:
                s["status"] = "CUMPLIDA"
                continue

            if tiempo >= 15:
                s["status"] = "EXPIRADA"
                continue

            # sigue activa
            señales_actualizadas.append(s)

        LiveSignalManager.active_signals = señales_actualizadas

        # 🆕 agregar nuevas señales
        for nueva in nuevas_senales:
            match_id = nueva["match"].get("match_id")
            market = nueva["match"].get("market")
            selection = nueva["match"].get("selection")

            existe = any(
                s["match"].get("match_id") == match_id
                and s["match"].get("market") == market
                and s["match"].get("selection") == selection
                for s in LiveSignalManager.active_signals
            )

            if not existe:
                nueva["created_at"] = ahora
                nueva["status"] = "ACTIVA"
                LiveSignalManager.active_signals.append(nueva)

        # ordenar por score
        LiveSignalManager.active_signals.sort(
            key=lambda x: x["match"].get("signal_score", 0),
            reverse=True
        )

        # top 6
        LiveSignalManager.active_signals = LiveSignalManager.active_signals[:6]

        return LiveSignalManager.active_signals
