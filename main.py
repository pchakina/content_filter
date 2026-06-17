import argparse
import logging
import sys
from pathlib import Path

from processor import XmlFilter


def main():
    parser = argparse.ArgumentParser(prog="content_filter")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--rules",      default=str(Path(__file__).parent / "rules.yaml"))
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--message-id", default=None)
    parser.add_argument("--log-file",   default=None)
    parser.add_argument("--log-level",  default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    handlers = [logging.StreamHandler(sys.stderr)]
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )

    xf = XmlFilter(args.rules)
    xf.process_file(args.input, args.output, dry_run=args.dry_run, message_id=args.message_id)


if __name__ == "__main__":
    main()
