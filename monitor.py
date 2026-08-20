"""
Completude new-student monitor.

Polls the Completude "cap/search" API for tutoring offers, and sends you an
email whenever a NEW offer appears within DISTANCE_THRESHOLD_KM of your
address.

Logs in automatically using COMPLETUDE_USERNAME / COMPLETUDE_PASSWORD, and
caches the token locally (token_cache.json) until it's about to expire.

Credentials (username, password, email settings) are read from environment
variables FIRST (this is how GitHub Actions Secrets get passed in), and fall
back to config.py if the environment variable isn't set (this is how it
still works when you just run it locally on your own computer for testing).
"""

import json
import os
import sys
import time
from datetime import datetime

import requests

import config

API_URL = "https://sic.internetude.fr/Api/ProfesseurCompletude/cap/search"
LOGIN_URL = "https://sic.internetude.fr/Api/ProfesseurCompletude/TokenAuth"

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.STATE_FILE)
TOKEN_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.TOKEN_CACHE_FILE)


def _cfg(name: str, default=None):
    """Read a setting from an environment variable first, falling back to
    config.py. This lets the exact same script work both locally (values
    come from config.py) and on GitHub Actions (values come from Secrets,
    injected as environment variables)."""
    env_val = os.environ.get(name)
    if env_val is not None and env_val != "":
        return env_val
    return getattr(config, name, default)


COMPLETUDE_USERNAME = _cfg("COMPLETUDE_USERNAME")
COMPLETUDE_PASSWORD = _cfg("COMPLETUDE_PASSWORD")
SMTP_USERNAME = _cfg("SMTP_USERNAME")
SMTP_APP_PASSWORD = _cfg("SMTP_APP_PASSWORD")
EMAIL_FROM = _cfg("EMAIL_FROM")
EMAIL_TO = _cfg("EMAIL_TO")


def load_seen_ids() -> set:
    if not os.path.exists(STATE_PATH):
        return set()
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        return set()


def save_seen_ids(seen_ids: set) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(seen_ids), f)


def login() -> str:
    """Log in with username/password and return a fresh access token."""
    payload = {
        "username": COMPLETUDE_USERNAME,
        "password": COMPLETUDE_PASSWORD,
        "grant_type": "password",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://professeur.completude.com",
        "Referer": "https://professeur.completude.com/",
    }

    resp = requests.post(LOGIN_URL, data=payload, headers=headers, timeout=15)

    if resp.status_code != 200:
        print(
            f"[ERROR] Login failed (status {resp.status_code}). "
            "Check COMPLETUDE_USERNAME / COMPLETUDE_PASSWORD.",
            file=sys.stderr,
        )
        sys.exit(1)

    data = resp.json()
    access_token = data["access_token"]
    expires_in = data.get("expires_in", 3599)

    cache = {
        "access_token": access_token,
        "expires_at": time.time() + expires_in - 60,  # 60s safety margin
    }
    with open(TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f)

    return access_token


def get_valid_token() -> str:
    """Return a cached token if still valid, otherwise log in for a new one."""
    if os.path.exists(TOKEN_CACHE_PATH):
        try:
            with open(TOKEN_CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if time.time() < cache.get("expires_at", 0):
                return cache["access_token"]
        except (json.JSONDecodeError, OSError, KeyError):
            pass
    return login()


def fetch_offers() -> list:
    payload = {
        "MapBox": config.MAP_BOX,
        "SessionRecherche": {
            **config.SESSION_RECHERCHE_EXTRA,
            "IdAdresse": config.ID_ADRESSE,
        },
    }

    def call_api(token: str):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://professeur.completude.com",
            "Referer": "https://professeur.completude.com/",
        }
        return requests.post(API_URL, json=payload, headers=headers, timeout=15)

    token = get_valid_token()
    resp = call_api(token)

    if resp.status_code == 401:
        token = login()
        resp = call_api(token)

    resp.raise_for_status()
    data = resp.json()
    return data.get("Demandes", [])


def send_email(subject: str, body: str) -> None:
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP_SSL(config.SMTP_SERVER, config.SMTP_PORT) as server:
        server.login(SMTP_USERNAME, SMTP_APP_PASSWORD)
        server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())


def send_email_with_retry(subject: str, body: str, attempts: int = 3) -> bool:
    for attempt in range(1, attempts + 1):
        try:
            send_email(subject, body)
            return True
        except Exception as e:
            print(f"[WARN] Email attempt {attempt}/{attempts} failed: {e}", file=sys.stderr)
            if attempt < attempts:
                time.sleep(5)
    return False


def format_message(offer: dict) -> str:
    return (
        f"Nouvel élève proche ({offer['Distance']:.1f} km) !\n"
        f"{offer.get('Ville', '?')} - {offer.get('LibelleCombinaison', '?')}\n"
        f"{offer.get('LibelleMatiere', '?')} - {offer.get('LibelleFrequence', '?')} "
        f"{offer.get('LibelleDuree', '')}\n"
        f"{offer.get('DetailPrix', '')}\n"
        f"Ref. {offer.get('IdDemande')}"
    )


def main():
    seen_ids = load_seen_ids()
    offers = fetch_offers()

    new_close_offers = [
        o for o in offers
        if o["IdDemande"] not in seen_ids and o.get("Distance", 999) <= config.DISTANCE_THRESHOLD_KM
    ]

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ids_pending_confirmation = {o["IdDemande"] for o in new_close_offers}
    seen_ids.update(o["IdDemande"] for o in offers if o["IdDemande"] not in ids_pending_confirmation)
    save_seen_ids(seen_ids)

    if not new_close_offers:
        print(f"[{timestamp}] No new nearby offers. ({len(offers)} total offers seen)")
        return

    for offer in new_close_offers:
        message = format_message(offer)
        print(f"[{timestamp}] NEW NEARBY OFFER:\n{message}\n")
        subject = f"Nouvel élève proche : {offer.get('Ville', '?')} ({offer['Distance']:.1f} km)"

        if send_email_with_retry(subject, message):
            seen_ids.add(offer["IdDemande"])
            save_seen_ids(seen_ids)
            print(f"[{timestamp}] Email sent successfully for Ref. {offer.get('IdDemande')}")
        else:
            print(
                f"[{timestamp}] FAILED to send email for Ref. {offer.get('IdDemande')} "
                "after all retries — will try again next run.",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
