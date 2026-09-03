"""
08_interactive_npi_lookup.py — Requirement: save chat history across runs,
and let the user drive an interactive practitioner lookup by NPI (basic
info, licenses, practice locations) turn by turn.

Chat history persistence uses strands.session.FileSessionManager — it
writes each message to a JSON file under SESSION_DIR, keyed by SESSION_ID.
Verified directly (not from memory) against the installed strands package:
constructing a brand-new Agent object with the same session_id/storage_dir
as a prior run automatically restores the full prior conversation into
agent.messages, before any model call happens.

Try it:
    1. Run this script, ask about a practitioner, then Ctrl+C / type "exit".
    2. Run it again — it remembers everything from step 1 and you can ask
       a follow-up ("what about his other licenses?") without re-stating
       who you're talking about.
    3. Change SESSION_ID (or delete the SESSION_DIR folder) to start fresh.

Setup (two terminals):
    Terminal 1:  python practitioner_stub_service.py
    Terminal 2:  python 08_interactive_npi_lookup.py
"""
from pathlib import Path

import requests
from strands import Agent, tool
from strands.models import BedrockModel
from strands.session import FileSessionManager

MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"   # swap if retired — see 00_setup.py
REGION = "us-east-1"
STUB_BASE_URL = "http://localhost:8000"

SESSION_ID = "practitioner-lookup-demo"
SESSION_DIR = str(Path(__file__).parent / "chat_sessions")


@tool
def get_practitioner_by_npi(npi: str) -> str:
    """Look up a practitioner's basic demographic info by their NPI number."""
    response = requests.get(f"{STUB_BASE_URL}/npi/{npi}", timeout=10)
    if response.status_code == 404:
        return f"No practitioner found for NPI {npi}."
    response.raise_for_status()
    return response.json()


@tool
def get_practitioner_licenses(npi: str) -> str:
    """Get all state medical licenses on file for a practitioner, by NPI."""
    response = requests.get(f"{STUB_BASE_URL}/npi/{npi}/licenses", timeout=10)
    if response.status_code == 404:
        return f"No practitioner found for NPI {npi}."
    response.raise_for_status()
    return response.json()


@tool
def get_practitioner_locations(npi: str) -> str:
    """Get all practice locations on file for a practitioner, by NPI."""
    response = requests.get(f"{STUB_BASE_URL}/npi/{npi}/locations", timeout=10)
    if response.status_code == 404:
        return f"No practitioner found for NPI {npi}."
    response.raise_for_status()
    return response.json()


model = BedrockModel(model_id=MODEL_ID, region_name=REGION)
session_manager = FileSessionManager(session_id=SESSION_ID, storage_dir=SESSION_DIR)

lookup_agent = Agent(
    name="npi_lookup_agent",
    description="Looks up practitioner demographics, licenses, and practice locations by NPI.",
    system_prompt=(
        "You help credentialing staff look up practitioners by NPI. You have three tools: "
        "get_practitioner_by_npi, get_practitioner_licenses, and get_practitioner_locations. "
        "Call whichever tool answers the user's question — don't call all three unless asked "
        "for a full profile. If the user refers to 'him'/'her'/'that practitioner' without "
        "repeating the NPI, use the NPI from earlier in this conversation."
    ),
    tools=[get_practitioner_by_npi, get_practitioner_licenses, get_practitioner_locations],
    model=model,
    session_manager=session_manager,
)

if __name__ == "__main__":
    if lookup_agent.messages:
        print(f"[Resumed session '{SESSION_ID}' — {len(lookup_agent.messages)} prior messages loaded]\n")
    else:
        print(f"[Starting new session '{SESSION_ID}']\n")

    print("Ask about a practitioner by NPI (e.g. 5555180777). Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue
        result = lookup_agent(user_input)
        print(f"\nAgent: {result}\n")
