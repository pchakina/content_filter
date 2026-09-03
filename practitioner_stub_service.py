"""
practitioner_stub_service.py — a local stand-in for the real practitioner
HTTP service. Lets 01_http_tool.py, 08_interactive_npi_lookup.py, and any
other example run without network access or hitting a public test API.

Zero extra dependencies — uses only the Python standard library.

Run:
    python practitioner_stub_service.py            # listens on port 8000
    python practitioner_stub_service.py 9000        # or a custom port

Try it directly in a browser or with curl while it's running:
    curl http://localhost:8000/practitioners/1
    curl http://localhost:8000/practitioners/999          # -> 404, not seeded
    curl http://localhost:8000/npi/5555180777
    curl http://localhost:8000/npi/5555180777/licenses
    curl http://localhost:8000/npi/5555180777/locations
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PRACTITIONERS = {
    1: {
        "id": 1,
        "first_name": "John",
        "last_name": "Nake",
        "npi": "5555180777",
        "license_state": "TN",
        "license_status": "Active",
        "email": "john.nake@example-clinic.test",
    },
    2: {
        "id": 2,
        "first_name": "Priya",
        "last_name": "Rao",
        "npi": "1122334455",
        "license_state": "CA",
        "license_status": "Active",
        "email": "priya.rao@example-clinic.test",
    },
    3: {
        "id": 3,
        "first_name": "Miguel",
        "last_name": "Santos",
        "npi": "9988776655",
        "license_state": "NV",
        "license_status": "Expired",
        "email": "miguel.santos@example-clinic.test",
    },
}

# NPI-keyed detail: demographics, multiple licenses, multiple practice locations.
PRACTITIONERS_BY_NPI = {
    "5555180777": {
        "npi": "5555180777",
        "first_name": "John",
        "middle_name": "Krishan",
        "last_name": "Nake",
        "provider_type": "MD",
        "primary_specialty": "Orthopaedic Surgery",
    },
    "1122334455": {
        "npi": "1122334455",
        "first_name": "Priya",
        "middle_name": None,
        "last_name": "Rao",
        "provider_type": "MD",
        "primary_specialty": "Family Medicine",
    },
    "9988776655": {
        "npi": "9988776655",
        "first_name": "Miguel",
        "middle_name": None,
        "last_name": "Santos",
        "provider_type": "DO",
        "primary_specialty": "Internal Medicine",
    },
}

LICENSES_BY_NPI = {
    "5555180777": [
        {"state": "TN", "license_number": "28855", "status": "Active", "expiration_date": "2026-10-31"},
        {"state": "NV", "license_number": "5213", "status": "Inactive", "expiration_date": "2025-06-30"},
        {"state": "AZ", "license_number": "33015", "status": "Active", "expiration_date": "2027-10-07"},
        {"state": "CA", "license_number": "G21984", "status": "Active", "expiration_date": "2026-10-31"},
    ],
    "1122334455": [
        {"state": "CA", "license_number": "A99231", "status": "Active", "expiration_date": "2027-03-15"},
    ],
    "9988776655": [
        {"state": "NV", "license_number": "N58120", "status": "Expired", "expiration_date": "2024-12-31"},
    ],
}

LOCATIONS_BY_NPI = {
    "5555180777": [
        {"practice_name": "Nashville Orthopaedic Group", "address": "1855 US Highway 51 Byp N",
         "city": "Dyersburg", "state": "TN", "primary": True},
        {"practice_name": "Music City Sports Medicine", "address": "5000 Crossings Cir",
         "city": "Mt Juliet", "state": "TN", "primary": False},
    ],
    "1122334455": [
        {"practice_name": "Bay Area Family Health", "address": "200 Ocean Ave",
         "city": "San Francisco", "state": "CA", "primary": True},
    ],
    "9988776655": [
        {"practice_name": "Desert Internal Medicine", "address": "700 Sahara Blvd",
         "city": "Las Vegas", "state": "NV", "primary": True},
    ],
}


class PractitionerHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parts = self.path.strip("/").split("/")

        if len(parts) == 2 and parts[0] == "practitioners":
            try:
                practitioner_id = int(parts[1])
            except ValueError:
                practitioner_id = None
            record = PRACTITIONERS.get(practitioner_id)
            if record is not None:
                self._send_json(200, record)
                return

        elif len(parts) == 2 and parts[0] == "npi":
            record = PRACTITIONERS_BY_NPI.get(parts[1])
            if record is not None:
                self._send_json(200, record)
                return

        elif len(parts) == 3 and parts[0] == "npi" and parts[2] == "licenses":
            if parts[1] in PRACTITIONERS_BY_NPI:
                self._send_json(200, {"npi": parts[1], "licenses": LICENSES_BY_NPI.get(parts[1], [])})
                return

        elif len(parts) == 3 and parts[0] == "npi" and parts[2] == "locations":
            if parts[1] in PRACTITIONERS_BY_NPI:
                self._send_json(200, {"npi": parts[1], "locations": LOCATIONS_BY_NPI.get(parts[1], [])})
                return

        self._send_json(404, {"error": f"No record at {self.path}"})

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - matches base signature
        print(f"[stub] {self.address_string()} - {format % args}")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer(("localhost", port), PractitionerHandler)
    print(f"Practitioner stub service running at http://localhost:{port}")
    print(f"Seeded IDs: {list(PRACTITIONERS.keys())}")
    print("Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
