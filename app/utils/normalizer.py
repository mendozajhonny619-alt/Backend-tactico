from difflib import SequenceMatcher

class Normalizer:
    @staticmethod
    def limpiar_nombre(nombre):
        if not nombre:
            return ""

        palabras_ruido = [
            "u20", "u23", "fc", "cf", "f.c.", "c.f.", "youth", "women",
            "femenino", "national team", "sub-20", "sub-23"
        ]

        nombre = nombre.lower().strip()
        for palabra in palabras_ruido:
            nombre = nombre.replace(palabra, "")

        return " ".join(nombre.split())

    @staticmethod
    def calcular_similitud(nombre_api, nombre_odds):
        n1 = Normalizer.limpiar_nombre(nombre_api)
        n2 = Normalizer.limpiar_nombre(nombre_odds)
        return SequenceMatcher(None, n1, n2).ratio()

    @staticmethod
    def match_profesional(api_local, api_visita, listado_odds):
        umbral = 0.82

        for partido_odds in listado_odds:
            score_local = Normalizer.calcular_similitud(api_local, partido_odds.get("home_team", ""))
            score_visita = Normalizer.calcular_similitud(api_visita, partido_odds.get("away_team", ""))

            if score_local >= umbral and score_visita >= umbral:
                return partido_odds

        return None
