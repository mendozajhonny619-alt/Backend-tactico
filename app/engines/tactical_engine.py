class TacticalEngine:
    @staticmethod
    def analizar_momentum(stats):
        ataques_p = stats.get("dangerous_attacks", 0)
        remates_total = stats.get("shots", 0)
        remates_arco = stats.get("shots_on_target", 0)
        minuto = stats.get("minute", 0)

        ppm = ataques_p / minuto if minuto and minuto > 0 else 0

        estado = "CONTROLADO"
        razon = "Ritmo estándar de juego"

        if ppm > 1.2 and remates_arco >= 3:
            estado = "EXPLOSIVO"
            razon = "Alta frecuencia de ataques peligrosos con puntería"
        elif ppm > 0.8:
            estado = "CALIENTE"
            razon = "Presión constante en área rival"
        elif ppm < 0.3 and minuto > 20:
            estado = "MUERTO"
            razon = "Falta de profundidad y ritmo"

        if ataques_p > 40 and remates_arco == 0:
            estado = "CAOS PELIGROSO"
            razon = "Ataques estériles, riesgo de contraataque"

        return {
            "match_state": estado,
            "match_state_reason": razon,
            "intensity_score": round(ppm * 10, 2),
            "shots": remates_total
        }

    @staticmethod
    def predictor_gol_inminente(stats):
        momentum = TacticalEngine.analizar_momentum(stats)

        es_inminente = False
        confianza_gol = 0

        if momentum["match_state"] == "EXPLOSIVO":
            es_inminente = True
            confianza_gol = 85
        elif momentum["match_state"] == "CALIENTE":
            es_inminente = True
            confianza_gol = 70

        return {
            "gol_inminente": es_inminente,
            "confianza_ventana": confianza_gol,
            "ventana_minutos": 10 if es_inminente else 0
          }
