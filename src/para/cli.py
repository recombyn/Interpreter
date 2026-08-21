from __future__ import annotations

import argparse
import json
from pathlib import Path

from para.app import Para
from para.paths import USER_DIR, set_user_dir


def build_para(args: argparse.Namespace) -> Para:
    user_dir = Path(args.user_dir) if getattr(args, "user_dir", None) else None
    return Para(
        remember=False,
        rules_path=Path(args.rules_path) if args.rules_path else None,
        infer_depth=args.infer_depth,
        load_user_docs=not getattr(args, "no_user_docs", False),
        user_dir=user_dir,
    )


def _run_gui(eng: Para) -> int:
    import tkinter as tk

    root = tk.Tk()
    root.title("Para")
    root.geometry("640x420")
    log = tk.Text(root, wrap="word")
    log.pack(fill="both", expand=True, padx=8, pady=8)
    log.configure(state="disabled")
    row = tk.Frame(root)
    row.pack(fill="x", padx=8, pady=(0, 8))
    entry = tk.Entry(row)
    entry.pack(side="left", fill="x", expand=True)
    entry.focus_set()

    def append(text: str) -> None:
        log.configure(state="normal")
        log.insert("end", text)
        log.see("end")
        log.configure(state="disabled")

    def send(_event=None) -> None:
        text = entry.get().strip()
        entry.delete(0, "end")
        if not text:
            return
        if text in {":q", ":quit"}:
            root.destroy()
            return
        reply = eng.reply(text)
        append(f"you:{text}\n")
        append(f"para:{reply}\n\n")

    tk.Button(row, text="send", command=send).pack(side="left", padx=(8, 0))
    entry.bind("<Return>", send)
    root.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Para: symbolic Chinese NLU (python -m para; no LLM)."
    )
    parser.add_argument("--rules-path", help="optional rules.tm path")
    parser.add_argument("--infer-depth", type=int, default=2, help="QP2 depth (default 2)")
    parser.add_argument(
        "--user-dir",
        default=None,
        help=f"host knowledge root (default: {USER_DIR})",
    )
    parser.add_argument(
        "--no-user-docs",
        action="store_true",
        help="skip loading knowledge/user memory .tm / docs",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    reply_p = sub.add_parser("reply", help="chat turn (read-only unless 教…)")
    reply_p.add_argument("text")
    reply_p.add_argument("--trace", action="store_true")

    teach_p = sub.add_parser("teach", help="write path (hear)")
    teach_p.add_argument("text")

    decode_p = sub.add_parser("decode", help="structured DecodeOutcome as JSON")
    decode_p.add_argument("text")
    decode_p.add_argument(
        "--write",
        choices=("auto", "true", "false"),
        default="auto",
        help="force write/read; default auto (教… → write)",
    )

    sub.add_parser("repl", help="interactive loop")
    sub.add_parser("gui", help="window")
    args = parser.parse_args(argv)

    if args.user_dir:
        set_user_dir(Path(args.user_dir))
    eng = build_para(args)

    if args.cmd == "reply":
        result = eng.interpret(args.text)
        if args.trace:
            print(f"notes: {result.notes}")
            print(f"reply: {result.reply}")
        else:
            print(result.reply)
        return 0

    if args.cmd == "teach":
        print(eng.teach(args.text))
        return 0

    if args.cmd == "decode":
        write: bool | None
        if args.write == "auto":
            write = None
        else:
            write = args.write == "true"
        out = eng.decode(args.text, write=write)
        print(json.dumps(out.to_dict(), ensure_ascii=False, indent=2))
        return 0 if out.ok or out.miss else 1

    if args.cmd == "gui":
        return _run_gui(eng)

    print("Para repl. :q quit | teach via 教… | decode JSON via :d …")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in {":q", ":quit"}:
            return 0
        if line.startswith(":d "):
            out = eng.decode(line[3:].strip())
            print(json.dumps(out.to_dict(), ensure_ascii=False, indent=2))
            continue
        print(eng.reply(line))
