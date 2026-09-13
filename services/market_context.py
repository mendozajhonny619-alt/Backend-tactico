class MarketContext:

    @staticmethod
    def evaluar(live_matches):
        total = len(live_matches or [])

        if total == 0:
            return {
                "mode": "MUERTO",
                "reason": "Sin partidos en vivo"
            }

        high_quality = 0
        mid_minutes = 0
        intensidad = 0

        for m in live_matches:
            minute = int(m.get("minute", 0) or 0)
            shots = int(m.get("shots_on_target", 0) or 0)
            danger = int(m.get("dangerous_attacks", 0) or 0)
            corners = int(m.get("corners", 0) or 0)

            if shots > 0 or danger > 10 or corners > 2:
                high_quality += 1

            if 25 <= minute <= 85:
                mid_minutes += 1

            if shots >= 2 or danger >= 15:
                intensidad += 1

        if high_quality >= 4 and intensidad >= 3:
            return {
                "mode": "FUERTE",
                "reason": "Muchos partidos con intensidad real"
            }

        if high_quality >= 2:
            return {
                "mode": "MEDIO",
                "reason": "Algunos partidos aprovechables"
            }

        return {
            "mode": "BAJO",
            "reason": "Poca actividad real en partidos"
          }
