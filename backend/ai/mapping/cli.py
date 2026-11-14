"""The four commands. Run from the backend folder:  python -m ai.mapping <command>

propose PSI-25                 ask the model for a mapping of the table of PSI-25
review PSI-25                  show the mapping next to sample values and the check results
approve PSI-25 --by <name>     approve it; refused on errors and on warnings that are not accepted
score                          compare the model's proposals with the gold mappings
"""
import argparse
import sys
from pathlib import Path

from . import store
from .approve import ApprovalRefused, approve
from .check import check_file
from .propose import ProposeFailed, propose
from .review import render_review
from .score import score
from .tables import TableError, read_table


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ai.mapping", description="T6 AI mapping assistant")
    commands = parser.add_subparsers(dest="command", required=True)

    def add(name, help_text, with_table=True):
        command = commands.add_parser(name, help=help_text)
        if with_table:
            command.add_argument("source_id", help="the PSI id of the table, for example PSI-25")
            command.add_argument("--table", type=Path, help="the table file; default: the file of that id in data/raw/")
        command.add_argument("--data-dir", type=Path, default=store.DEFAULT_DATA_DIR, help="default: the repo's data/ folder")
        return command

    command = add("propose", "ask the model for a mapping")
    command.add_argument("--force", action="store_true", help="replace an existing mapping file")
    add("review", "show a mapping with sample values and check results")
    command = add("approve", "approve a mapping by name")
    command.add_argument("--by", required=True, help="the name of the person who approves")
    command.add_argument("--accept", action="append", default=[], metavar="WARNING", help="accept one warning by its name; repeat for more")
    add("score", "score the proposals against the gold mappings", with_table=False)
    return parser


def _show_check(result) -> None:
    print("Errors: none" if not result.errors else "Errors:")
    for error in result.errors:
        print(f"  - {error}")
    print("Warnings: none" if not result.warnings else "Warnings (settle each one before approval):")
    for key, text in result.warnings.items():
        print(f"  - {key}  ({text})")


def main(argv=None) -> int:
    """Run one command and return its exit code. It reads no .env file; __main__ does that."""
    args = _parser().parse_args(argv)
    try:
        if args.command == "score":
            report = score(args.data_dir)
            print(report.render())
            return 1 if report.errors else 0

        table_path = args.table or store.find_table(args.data_dir, args.source_id)
        if args.command == "propose":
            result = propose(args.source_id, table_path, args.data_dir, force=args.force)
            print(f"Wrote {result.path}")
            print(f"Untouched copy: {result.copy_path}")
            _show_check(result.check)
            print(f"Next: python -m ai.mapping review {args.source_id}")
        elif args.command == "review":
            table = read_table(table_path)
            path = store.mapping_path(args.data_dir, args.source_id)
            result = check_file(path, table)
            try:
                mapping = store.read_mapping(path)
            except (OSError, ValueError):
                _show_check(result)
                return 1
            print(render_review(mapping, table, result))
        elif args.command == "approve":
            approved = approve(args.source_id, args.data_dir, by=args.by, accept=args.accept, table_path=args.table)
            print(f"Approved {args.source_id} by {approved.approved_by} at {approved.approved_at}.")
    except (ProposeFailed, ApprovalRefused, TableError) as error:
        print(f"Not done. {error}", file=sys.stderr)
        return 1
    return 0
