#!/usr/bin/env python3
"""Fail if syncing the committed KiCad PCB from Stackup would change it.

Run with KiCad 10's Python. The plugin's normal update runs on a board in memory; this
script never calls SaveBoard, so it does not rewrite the PCB or project.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("--stackup", required=True, type=Path, help="Cargo-locked Stackup CLI")
    parser.add_argument("--plugin-dir", required=True, type=Path, help="Stackup KiCad plugin")
    args = parser.parse_args()

    board_path = args.board.resolve()
    cli = args.stackup.resolve()
    plugin_dir = args.plugin_dir.resolve()
    if not board_path.is_file() or not cli.is_file() or not (plugin_dir / "sync_headless.py").is_file():
        parser.error("board, Stackup CLI, and plugin directory must exist")

    import pcbnew

    if pcbnew.GetMajorMinorVersion().split(".")[0] != "10":
        parser.error(f"the PCB requires KiCad 10; found {pcbnew.GetBuildVersion()}")

    sys.path.insert(0, str(plugin_dir))
    import sync_headless

    board_config, netlist, apply_module = sync_headless.plugin_modules()
    link = board_config.parse_link(board_config.link_of(board_path), board_path)
    result = subprocess.run(
        [str(cli), "netlist", str(link.file), "--locked"],
        cwd=link.directory,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        print(result.stderr or result.stdout, file=sys.stderr)
        return 1
    components = netlist.parse(result.stdout)
    if not components:
        print("Stackup exported no components", file=sys.stderr)
        return 1

    board = pcbnew.LoadBoard(str(board_path))
    outcome = apply_module.apply(board, components, netlist.classes(result.stdout))
    print(outcome.summary())
    if outcome.classed.problems:
        print("\n".join(outcome.classed.problems), file=sys.stderr)
    changed = any(
        (
            outcome.placed,
            outcome.updated,
            outcome.deleted,
            outcome.rebodied,
            outcome.nets_created,
            outcome.rewired,
            outcome.renamed,
            outcome.recoppered,
            outcome.nets_removed,
            outcome.orphaned,
            outcome.classed.changed(),
            outcome.classed.problems,
            outcome.problems,
        )
    )
    if changed:
        print("PCB differs from Stackup; sync it in KiCad and commit the PCB", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
