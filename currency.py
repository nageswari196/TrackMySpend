"""
Currency conversion, replacing forex_python (which relies on a free API that
has been unreliable/defunct for a while and has no caching, causing OCR
receipt parsing to hang or crash).

Uses exchangerate.host (free, keyless, actively maintained) with an in-memory
cache and a static fallback table so the app degrades gracefully offline.
"""
import requests
import streamlit as st
import config

@st.cache_data(ttl=3600)  # refresh rates at most once an hour
def _get_rate(from_currency: str, to_currency: str) -> float:
    try:
        resp = requests.get(
            config.EXCHANGE_RATE_API,
            params={"base": from_currency, "symbols": to_currency},
            timeout=4,
        )
        resp.raise_for_status()
        data = resp.json()
        return float(data["rates"][to_currency])
    except Exception:
        # Offline / API-down fallback
        return config.FALLBACK_RATES_TO_INR.get(from_currency, 1.0)

def convert_to_inr(amount: float, from_currency: str) -> float:
    if from_currency == "INR":
        return amount
    rate = _get_rate(from_currency, "INR")
    return round(amount * rate, 2)
