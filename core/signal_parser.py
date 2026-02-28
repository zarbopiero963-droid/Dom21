import re

class SignalParser:
    @staticmethod
    def parse_basic(text: str) -> dict:
        if not text: return {}
        result = {}
        text_clean = text.strip()
        
        teams_match = re.search(r"(?:🆚|VS|vs|⚽)\s*(.*?)(?:\n|$)", text_clean, re.IGNORECASE)
        if teams_match: result["teams"] = teams_match.group(1).strip()
        else:
            lines = [line.strip() for line in text_clean.split('\n') if line.strip()]
            result["teams"] = lines[0] if lines else "Match Sconosciuto"

        score_match = re.search(r"(\d+)\s*-\s*(\d+)", text_clean)
        if score_match:
            try: result["market"] = f"Over {int(score_match.group(1)) + int(score_match.group(2))}.5"
            except: result["market"] = "Over 0.5"
        return result