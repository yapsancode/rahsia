"""Command line: python -m profile_builder --role seeker --file notes.txt

The person reviews the profile before it counts as `reviewed`.
"""
import argparse
import json
import sys
from pathlib import Path

from .builder import DEFAULT_MODEL, build_profile, diff_profiles
from .client import RunnerError


def main() -> int:
    parser = argparse.ArgumentParser(prog="profile_builder", description=__doc__)
    parser.add_argument("--role", required=True, choices=["seeker", "provider"])
    parser.add_argument("--file", help="notes file (UTF-8). Reads standard input if missing.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out", help="write the profile JSON here (fake data only in this repo)")
    parser.add_argument("--twice", action="store_true",
                        help="run two times and show where the model disagrees with itself")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--yes", action="store_true", help="mark as reviewed without asking")
    args = parser.parse_args()

    notes = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    try:
        first = build_profile(notes, args.role, args.model, seed=0, temperature=args.temperature)
        second = build_profile(notes, args.role, args.model, seed=1, temperature=args.temperature) \
            if args.twice else None
    except RunnerError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    for warning in first.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if not first.ok:
        print("Could not build a valid profile:", file=sys.stderr)
        for error in first.errors:
            print(f"  - {error}", file=sys.stderr)
        print(f"Model said: {first.raw[:300]!r}", file=sys.stderr)
        return 1

    print(first.profile.model_dump_json(indent=2))
    print(f"\n{first.seconds}s with {first.model}", file=sys.stderr)

    if second is not None:
        if not second.ok:
            print("Second run gave no valid profile.", file=sys.stderr)
        else:
            diff = diff_profiles(first.profile, second.profile)
            print(f"Second run disagrees on {len(diff)} field(s): {json.dumps(diff, ensure_ascii=False)}",
                  file=sys.stderr)

    if args.yes:
        first.profile.reviewed = True
    elif sys.stdin.isatty():
        try:
            first.profile.reviewed = input("Is this profile correct? [y/N] ").strip().lower() == "y"
        except EOFError:  # no keyboard attached: leave it unreviewed
            pass
    if args.out:
        Path(args.out).write_text(first.profile.model_dump_json(indent=2), encoding="utf-8")
        print(f"Saved to {args.out} (reviewed={first.profile.reviewed})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
