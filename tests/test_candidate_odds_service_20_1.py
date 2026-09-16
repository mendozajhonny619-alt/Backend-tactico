from app.v17.services.candidate_odds_service import CandidateOddsService


def test_api_football_totals_parser_reads_real_line_and_price():
    service = CandidateOddsService()
    raw = [{
        "bookmakers": [{
            "name": "Bet365",
            "bets": [{
                "name": "Goals Over/Under",
                "values": [
                    {"value": "Over 2.5", "odd": "1.82"},
                    {"value": "Under 2.5", "odd": "1.95"},
                ],
            }],
        }],
    }]
    over = service._extract_totals(raw, "OVER")
    under = service._extract_totals(raw, "UNDER")
    assert any(x["line"] == 2.5 and x["odds"] == 1.82 for x in over)
    assert any(x["line"] == 2.5 and x["odds"] == 1.95 for x in under)
