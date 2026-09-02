# -----------------------------------------------------------------------------
# CONFIGURATION — fill in your own values below
# -----------------------------------------------------------------------------

# --- Completude API auth ---
# The script logs in automatically using these, and caches a fresh token
# in token_cache.json until it's about to expire.
# NOTE: stored in plain text — never upload this file with real values
# filled in anywhere public (e.g. a public GitHub repo).
COMPLETUDE_USERNAME = "username"
COMPLETUDE_PASSWORD = "PASTE_YOUR_COMPLETUDE_PASSWORD_HERE"

# --- Search parameters (from your captured request) ---
# Not sensitive credentials, just search settings — safe to keep as-is.
ID_ADRESSE = 1933461

MAP_BOX = {
    "IdSessionRecherche": 0,
    "NordOuestLatitude": 49.239893638535754,
    "NordOuestLongitude": 1.63548071546243,
    "SudEstLatitude": 48.34157836146425,
    "SudEstLongitude": 2.9990206845375704,
}

SESSION_RECHERCHE_EXTRA = {
    "Id": 0,
    "AvecChat": True,
    "AvecChien": True,
    "AvecVehicule": False,
    "DispoSemaine": True,
    "DispoVacance": True,
    "DispoWeekEnd": True,
}

# --- Filtering ---
DISTANCE_THRESHOLD_KM = 9.0

# --- Email notifications (free, via SMTP) ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # SSL port — works better on restrictive networks than 587
SMTP_USERNAME = "your.email@gmail.com"
SMTP_APP_PASSWORD = "PASTE_YOUR_16_CHAR_APP_PASSWORD"
EMAIL_FROM = "your.email@gmail.com"
EMAIL_TO = "your.email@gmail.com"

# --- Local state files ---
STATE_FILE = "seen_offers.json"
TOKEN_CACHE_FILE = "token_cache.json"
