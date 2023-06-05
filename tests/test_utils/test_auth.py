from __future__ import annotations

import pytest

from src.utils.auth import TokenInvalidException, get_token_payload

REAL_TOKEN = """eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjI0ODFGVEVuYjNlZEhaanBxcktYRSJ9.eyJpc3MiOiJodHRwczovL2Rldi03MmRwYmZ2Yi51cy5hdXRoMC5jb20vIiwic3ViIjoiQUlHczVPSzQ1WmFBd202d0U2bWxrc0NiMEhidjZkVVJAY2xpZW50cyIsImF1ZCI6Imh0dHBzOi8vYXBpLm5pZ2h0aW5nYWxlLnh5eiIsImlhdCI6MTY4NTgyMzUwNiwiZXhwIjoxNjg1OTA5OTA2LCJhenAiOiJBSUdzNU9LNDVaYUF3bTZ3RTZtbGtzQ2IwSGJ2NmRVUiIsImd0eSI6ImNsaWVudC1jcmVkZW50aWFscyJ9.qmpn2wDcfRtM0jnVOyJ4j6VLU_n0c53SI9pgBf9HKzpWvWhamSUzvw_qgN-QD0TVhm8YCYBodP-Qg-27CIMzcH0-deZmLRhQwMb5tQkll94JSs44cgay5CZnaI9pZ5RDtlbLNMImcw7DkEz_eHiffmICt-OmDrfE3crc_ns3Aatp9HEqTolNPrES-vUSySDTB4j0OH6IstcTeX0Ha9CfDk8VXOLOPUQur2tM4sUYk--Gboz59m62_tEt_0vhIUhJ9QGyiWIas_7t0H0cXvXdaP-t7pqHAkjdgad6IwrMJExeLPeZF7S-9tWsOYPutieYJ-TW8cOJlHT3LtOqX0OZ5w"""


def test_get_token_payload_fail():
    with pytest.raises(TokenInvalidException):
        get_token_payload("fake token")


def test_get_token_payload():
    assert isinstance(get_token_payload(REAL_TOKEN), dict)
