from __future__ import annotations

from typing import Any, Dict, List


class PlayerLiveAnalyzer:
    """
    Analizador auxiliar de rendimiento individual live.

    No bloquea.
    No crea señales.
    No modifica probabilidades.
    Solo entrega lectura avanzada usando datos de /fixtures/players.
    """

    def analyze(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
    ) -> Dict[str, Any]:
        match = match or {}
        context = context or {}
        ai = ai or {}

        players_data = match.get("players") if isinstance(match.get("players"), list) else []

        if not players_data:
            return self._empty_result()

        home_team_id = match.get("home_id")
        away_team_id = match.get("away_id")

        home_players = self._team_players(players_data, home_team_id, index=0)
        away_players = self._team_players(players_data, away_team_id, index=1)

        home_profile = self._team_profile(home_players)
        away_profile = self._team_profile(away_players)

        attacking_side = self._attacking_side(
            home_profile=home_profile,
            away_profile=away_profile,
            context=context,
        )

        vulnerability_side = self._vulnerability_side(
            home_profile=home_profile,
            away_profile=away_profile,
        )

        player_pressure_signal = self._player_pressure_signal(
            home_profile=home_profile,
            away_profile=away_profile,
            context=context,
        )

        fatigue_signal = self._fatigue_signal(
            home_profile=home_profile,
            away_profile=away_profile,
        )

        key_players = self._key_players(home_players, away_players)

        summary = self._summary(
            attacking_side=attacking_side,
            vulnerability_side=vulnerability_side,
            player_pressure_signal=player_pressure_signal,
            fatigue_signal=fatigue_signal,
            key_players=key_players,
        )

        return {
            "player_analysis_enabled": True,
            "player_data_available": True,

            "player_attacking_side": attacking_side,
            "player_vulnerability_side": vulnerability_side,
            "player_pressure_signal": player_pressure_signal,
            "player_fatigue_signal": fatigue_signal,

            "home_player_profile": home_profile,
            "away_player_profile": away_profile,
            "key_live_players": key_players,

            "player_analysis_summary": summary,
        }

    def _team_players(
        self,
        players_data: List[Dict[str, Any]],
        team_id: Any,
        index: int,
    ) -> List[Dict[str, Any]]:
        if team_id is not None:
            for entry in players_data:
                team = entry.get("team") if isinstance(entry.get("team"), dict) else {}
                if str(team.get("id")) == str(team_id):
                    return entry.get("players", []) if isinstance(entry.get("players"), list) else []

        if len(players_data) > index:
            entry = players_data[index] or {}
            return entry.get("players", []) if isinstance(entry.get("players"), list) else []

        return []

    def _team_profile(self, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        starters = 0
        subs = 0
        total_rating = 0.0
        rated_count = 0

        shots = 0.0
        shots_on = 0.0
        goals = 0.0
        assists = 0.0
        key_passes = 0.0
        total_passes = 0.0
        pass_accuracy_sum = 0.0
        pass_accuracy_count = 0

        tackles = 0.0
        blocks = 0.0
        interceptions = 0.0
        duels_total = 0.0
        duels_won = 0.0
        dribbles_attempts = 0.0
        dribbles_success = 0.0
        fouls_drawn = 0.0
        fouls_committed = 0.0
        yellow_cards = 0.0
        red_cards = 0.0

        active_attackers = 0
        defensive_load = 0.0
        offensive_load = 0.0
        discipline_risk = 0.0

        for item in players:
            player = item.get("player") if isinstance(item.get("player"), dict) else {}
            stats_list = item.get("statistics") if isinstance(item.get("statistics"), list) else []

            stats = stats_list[0] if stats_list else {}
            games = stats.get("games") if isinstance(stats.get("games"), dict) else {}
            shots_data = stats.get("shots") if isinstance(stats.get("shots"), dict) else {}
            goals_data = stats.get("goals") if isinstance(stats.get("goals"), dict) else {}
            passes_data = stats.get("passes") if isinstance(stats.get("passes"), dict) else {}
            tackles_data = stats.get("tackles") if isinstance(stats.get("tackles"), dict) else {}
            duels_data = stats.get("duels") if isinstance(stats.get("duels"), dict) else {}
            dribbles_data = stats.get("dribbles") if isinstance(stats.get("dribbles"), dict) else {}
            fouls_data = stats.get("fouls") if isinstance(stats.get("fouls"), dict) else {}
            cards_data = stats.get("cards") if isinstance(stats.get("cards"), dict) else {}

            if bool(games.get("substitute")):
                subs += 1
            else:
                starters += 1

            rating = self._safe_float(games.get("rating"))
            if rating > 0:
                total_rating += rating
                rated_count += 1

            pos = str(games.get("position") or player.get("pos") or "").upper()

            player_shots = self._safe_float(shots_data.get("total"))
            player_shots_on = self._safe_float(shots_data.get("on"))
            player_goals = self._safe_float(goals_data.get("total"))
            player_assists = self._safe_float(goals_data.get("assists"))
            player_key_passes = self._safe_float(passes_data.get("key"))

            shots += player_shots
            shots_on += player_shots_on
            goals += player_goals
            assists += player_assists
            key_passes += player_key_passes
            total_passes += self._safe_float(passes_data.get("total"))

            accuracy = self._safe_float(passes_data.get("accuracy"))
            if accuracy > 0:
                pass_accuracy_sum += accuracy
                pass_accuracy_count += 1

            tackles += self._safe_float(tackles_data.get("total"))
            blocks += self._safe_float(tackles_data.get("blocks"))
            interceptions += self._safe_float(tackles_data.get("interceptions"))

            duel_total = self._safe_float(duels_data.get("total"))
            duel_won = self._safe_float(duels_data.get("won"))
            duels_total += duel_total
            duels_won += duel_won

            dribble_attempts = self._safe_float(dribbles_data.get("attempts"))
            dribble_success = self._safe_float(dribbles_data.get("success"))
            dribbles_attempts += dribble_attempts
            dribbles_success += dribble_success

            fouls_drawn += self._safe_float(fouls_data.get("drawn"))
            fouls_committed += self._safe_float(fouls_data.get("committed"))

            yellow = self._safe_float(cards_data.get("yellow"))
            red = self._safe_float(cards_data.get("red"))
            yellow_cards += yellow
            red_cards += red

            offensive_score = (
                player_shots * 1.4
                + player_shots_on * 2.4
                + player_key_passes * 1.6
                + player_goals * 3.0
                + player_assists * 2.5
                + dribble_success * 1.2
            )

            defensive_score = (
                self._safe_float(tackles_data.get("total")) * 1.2
                + self._safe_float(tackles_data.get("blocks")) * 1.4
                + self._safe_float(tackles_data.get("interceptions")) * 1.4
                + max(0.0, duel_total - duel_won) * 0.5
                + yellow * 2.0
                + red * 5.0
            )

            if pos in {"F", "M", "AM", "FW"} and offensive_score >= 3.0:
                active_attackers += 1

            offensive_load += offensive_score
            defensive_load += defensive_score
            discipline_risk += yellow * 2.0 + red * 8.0 + self._safe_float(fouls_data.get("committed")) * 0.4

        average_rating = total_rating / rated_count if rated_count else 0.0
        pass_accuracy = pass_accuracy_sum / pass_accuracy_count if pass_accuracy_count else 0.0
        duel_success_rate = (duels_won / duels_total * 100.0) if duels_total > 0 else 0.0
        dribble_success_rate = (dribbles_success / dribbles_attempts * 100.0) if dribbles_attempts > 0 else 0.0

        return {
            "players_count": len(players),
            "starters_count": starters,
            "substitutes_count": subs,
            "average_rating": round(average_rating, 2),

            "shots": round(shots, 2),
            "shots_on_target": round(shots_on, 2),
            "goals": round(goals, 2),
            "assists": round(assists, 2),
            "key_passes": round(key_passes, 2),
            "total_passes": round(total_passes, 2),
            "pass_accuracy": round(pass_accuracy, 2),

            "tackles": round(tackles, 2),
            "blocks": round(blocks, 2),
            "interceptions": round(interceptions, 2),
            "duels_total": round(duels_total, 2),
            "duels_won": round(duels_won, 2),
            "duel_success_rate": round(duel_success_rate, 2),

            "dribbles_attempts": round(dribbles_attempts, 2),
            "dribbles_success": round(dribbles_success, 2),
            "dribble_success_rate": round(dribble_success_rate, 2),

            "fouls_drawn": round(fouls_drawn, 2),
            "fouls_committed": round(fouls_committed, 2),
            "yellow_cards": round(yellow_cards, 2),
            "red_cards": round(red_cards, 2),

            "active_attackers": active_attackers,
            "offensive_load": round(offensive_load, 2),
            "defensive_load": round(defensive_load, 2),
            "discipline_risk": round(discipline_risk, 2),
        }

    def _attacking_side(
        self,
        home_profile: Dict[str, Any],
        away_profile: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        context_attack_side = str(context.get("attack_side") or "BALANCED").upper()

        home_score = (
            self._safe_float(home_profile.get("offensive_load"))
            + self._safe_float(home_profile.get("shots_on_target")) * 1.5
            + self._safe_float(home_profile.get("key_passes")) * 1.2
            + self._safe_float(home_profile.get("active_attackers")) * 2.0
        )

        away_score = (
            self._safe_float(away_profile.get("offensive_load"))
            + self._safe_float(away_profile.get("shots_on_target")) * 1.5
            + self._safe_float(away_profile.get("key_passes")) * 1.2
            + self._safe_float(away_profile.get("active_attackers")) * 2.0
        )

        if context_attack_side == "HOME":
            home_score += 4
        elif context_attack_side == "AWAY":
            away_score += 4

        diff = home_score - away_score

        if diff >= 6:
            return "HOME"
        if diff <= -6:
            return "AWAY"
        return "BALANCED"

    def _vulnerability_side(
        self,
        home_profile: Dict[str, Any],
        away_profile: Dict[str, Any],
    ) -> str:
        home_vulnerability = (
            self._safe_float(home_profile.get("defensive_load"))
            + self._safe_float(home_profile.get("discipline_risk"))
            + max(0.0, 50.0 - self._safe_float(home_profile.get("duel_success_rate"))) * 0.2
        )

        away_vulnerability = (
            self._safe_float(away_profile.get("defensive_load"))
            + self._safe_float(away_profile.get("discipline_risk"))
            + max(0.0, 50.0 - self._safe_float(away_profile.get("duel_success_rate"))) * 0.2
        )

        diff = home_vulnerability - away_vulnerability

        if diff >= 6:
            return "HOME_DEFENSE"
        if diff <= -6:
            return "AWAY_DEFENSE"
        return "BALANCED"

    def _player_pressure_signal(
        self,
        home_profile: Dict[str, Any],
        away_profile: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))

        total_offensive_load = (
            self._safe_float(home_profile.get("offensive_load"))
            + self._safe_float(away_profile.get("offensive_load"))
        )

        total_key_passes = (
            self._safe_float(home_profile.get("key_passes"))
            + self._safe_float(away_profile.get("key_passes"))
        )

        active_attackers = (
            self._safe_int(home_profile.get("active_attackers"))
            + self._safe_int(away_profile.get("active_attackers"))
        )

        if pressure >= 22 and rhythm >= 14 and total_offensive_load >= 18:
            return "STRONG_PLAYER_SUPPORT"

        if pressure >= 16 and total_key_passes >= 3 and active_attackers >= 2:
            return "PLAYER_SUPPORT"

        if total_offensive_load <= 6 and pressure <= 12:
            return "WEAK_PLAYER_SUPPORT"

        return "NEUTRAL"

    def _fatigue_signal(
        self,
        home_profile: Dict[str, Any],
        away_profile: Dict[str, Any],
    ) -> str:
        total_fouls = (
            self._safe_float(home_profile.get("fouls_committed"))
            + self._safe_float(away_profile.get("fouls_committed"))
        )

        total_cards = (
            self._safe_float(home_profile.get("yellow_cards"))
            + self._safe_float(away_profile.get("yellow_cards"))
            + self._safe_float(home_profile.get("red_cards")) * 2
            + self._safe_float(away_profile.get("red_cards")) * 2
        )

        duel_rate_avg = (
            self._safe_float(home_profile.get("duel_success_rate"))
            + self._safe_float(away_profile.get("duel_success_rate"))
        ) / 2

        if total_cards >= 5 or total_fouls >= 28:
            return "HIGH_GAME_STRESS"

        if duel_rate_avg > 0 and duel_rate_avg < 42:
            return "DUEL_FATIGUE_RISK"

        if total_fouls >= 18:
            return "MEDIUM_GAME_STRESS"

        return "NORMAL"

    def _key_players(
        self,
        home_players: List[Dict[str, Any]],
        away_players: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        combined = []

        for side, players in [("HOME", home_players), ("AWAY", away_players)]:
            for item in players:
                player = item.get("player") if isinstance(item.get("player"), dict) else {}
                stats_list = item.get("statistics") if isinstance(item.get("statistics"), list) else []
                stats = stats_list[0] if stats_list else {}

                games = stats.get("games") if isinstance(stats.get("games"), dict) else {}
                shots_data = stats.get("shots") if isinstance(stats.get("shots"), dict) else {}
                goals_data = stats.get("goals") if isinstance(stats.get("goals"), dict) else {}
                passes_data = stats.get("passes") if isinstance(stats.get("passes"), dict) else {}
                dribbles_data = stats.get("dribbles") if isinstance(stats.get("dribbles"), dict) else {}
                tackles_data = stats.get("tackles") if isinstance(stats.get("tackles"), dict) else {}
                cards_data = stats.get("cards") if isinstance(stats.get("cards"), dict) else {}

                score = (
                    self._safe_float(games.get("rating")) * 2.0
                    + self._safe_float(shots_data.get("on")) * 3.0
                    + self._safe_float(shots_data.get("total")) * 1.2
                    + self._safe_float(goals_data.get("total")) * 4.0
                    + self._safe_float(goals_data.get("assists")) * 3.0
                    + self._safe_float(passes_data.get("key")) * 2.0
                    + self._safe_float(dribbles_data.get("success")) * 1.5
                    + self._safe_float(tackles_data.get("interceptions")) * 1.0
                    - self._safe_float(cards_data.get("red")) * 4.0
                )

                if score <= 0:
                    continue

                combined.append(
                    {
                        "side": side,
                        "player_id": player.get("id"),
                        "name": player.get("name") or "N/A",
                        "position": games.get("position") or "N/A",
                        "rating": self._safe_float(games.get("rating")),
                        "impact_score": round(score, 2),
                        "shots_on_target": self._safe_float(shots_data.get("on")),
                        "shots": self._safe_float(shots_data.get("total")),
                        "key_passes": self._safe_float(passes_data.get("key")),
                    }
                )

        combined.sort(key=lambda x: x.get("impact_score", 0), reverse=True)
        return combined[:5]

    def _summary(
        self,
        attacking_side: str,
        vulnerability_side: str,
        player_pressure_signal: str,
        fatigue_signal: str,
        key_players: List[Dict[str, Any]],
    ) -> str:
        if player_pressure_signal == "STRONG_PLAYER_SUPPORT":
            return f"Soporte individual fuerte para presión ofensiva. Lado ofensivo: {attacking_side}."

        if player_pressure_signal == "PLAYER_SUPPORT":
            return f"Hay soporte individual moderado para la lectura ofensiva. Lado: {attacking_side}."

        if player_pressure_signal == "WEAK_PLAYER_SUPPORT":
            return "Los datos individuales no sostienen una presión ofensiva fuerte."

        if fatigue_signal in {"HIGH_GAME_STRESS", "DUEL_FATIGUE_RISK"}:
            return f"Partido con señales de estrés físico/disciplinario. Vulnerabilidad: {vulnerability_side}."

        if key_players:
            top = key_players[0]
            return f"Jugador más influyente: {top.get('name')} ({top.get('side')}) con impacto {top.get('impact_score')}."

        return "Lectura individual neutral, sin jugador dominante claro."

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "player_analysis_enabled": True,
            "player_data_available": False,
            "player_attacking_side": "UNKNOWN",
            "player_vulnerability_side": "UNKNOWN",
            "player_pressure_signal": "NO_PLAYER_DATA",
            "player_fatigue_signal": "UNKNOWN",
            "home_player_profile": {},
            "away_player_profile": {},
            "key_live_players": [],
            "player_analysis_summary": "Sin datos individuales disponibles para este partido.",
        }

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except Exception:
            return 0
