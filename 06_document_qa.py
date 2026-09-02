"""
06_document_qa.py — Requirement: read a document, summarize it, and answer
any questions asked about it.

A single @tool-decorated function extracts text from either a .txt/.md file
or a .pdf (via pypdf), and the agent is instructed to always summarize
first, then answer whatever specific question it was asked from the
document content — saying so explicitly if the answer isn't in the document,
rather than guessing.

Two sample documents are included in sample_docs/:
    - credentialing_policy.txt       (plain text)
    - practitioner_cvo_report.pdf    (PDF — a fictitious CVO verification
                                       report; the last line of the PDF
                                       itself confirms all data is fictitious)

Setup:
    pip install strands-agents boto3 pypdf
    (configure AWS credentials — see 00_setup.py)

Run:
    python 06_document_qa.py
"""
from pathlib import Path

from strands import Agent, tool
from strands.models import BedrockModel

MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"   # swap if retired — see 00_setup.py
REGION = "us-east-1"
SAMPLE_DOCS = Path(__file__).parent / "sample_docs"


@tool
def read_document(file_path: str) -> str:
    """Read a local .txt, .md, or .pdf file and return its full text content."""
    path = Path(file_path)
    if not path.exists():
        return f"Error: no file found at {file_path}"

    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    return path.read_text(encoding="utf-8")


model = BedrockModel(model_id=MODEL_ID, region_name=REGION)

document_assistant = Agent(
    name="document_assistant",
    description="Reads a document, summarizes it, and answers questions about it.",
    system_prompt=(
        "You read documents using the read_document tool. Always: "
        "1) summarize the document in 3-5 sentences, then "
        "2) answer the specific question you were asked, using only the document's "
        "content. If the document does not contain the answer, say so explicitly "
        "instead of guessing."
    ),
    tools=[read_document],
    model=model,
)

if __name__ == "__main__":
    print("=== Plain text document ===")
    result_txt = document_assistant(
        f"Read {SAMPLE_DOCS / 'credentialing_policy.txt'} and summarize it. "
        "Then answer: does a lapsed subspecialty certification automatically "
        "disqualify an applicant?"
    )
    print("\n--- RESULT (text) ---")
    print(result_txt)

    print("\n\n=== PDF document ===")
    result_pdf = document_assistant(
        f"Read {SAMPLE_DOCS / 'practitioner_cvo_report.pdf'} and summarize it. "
        "Then answer: is Dr. Mitchell eligible for Infectious Disease privileges "
        "right now, and why or why not?"
    )
    print("\n--- RESULT (pdf) ---")
    print(result_pdf)
