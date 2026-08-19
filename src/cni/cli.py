from __future__ import annotations

import argparse
from pathlib import Path

from cni.interpreter import Interpreter


def build_interpreter(args: argparse.Namespace) -> Interpreter:
    return Interpreter(
        remember=True,
        rules_path=Path(args.rules_path) if args.rules_path else None,
        infer_depth=args.infer_depth,
    )


def _run_gui(interp: Interpreter) -> int:
    import tkinter as tk

    root = tk.Tk()
    root.title("cni")
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
        reply = interp.reply(text)
        append(f"you:{text}\n")
        append(f"cni:{reply}\n\n")

    tk.Button(row, text="send", command=send).pack(side="left", padx=(8, 0))
    entry.bind("<Return>", send)
    root.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UTF-8 in, machine world, UTF-8 out.")
    parser.add_argument(
        "--rules-path",
        help="optional rule file path (defaults to knowledge/world/rules.tm)",
    )
    parser.add_argument(
        "--infer-depth",
        type=int,
        default=2,
        help="forward inference depth cap (0 disables inference)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    reply_p = sub.add_parser("reply", help="one-shot reply")
    reply_p.add_argument("text")
    reply_p.add_argument("--trace", action="store_true")
    sub.add_parser("repl", help="interactive loop")
    sub.add_parser("gui", help="window with a text box")
    args = parser.parse_args(argv)
    interp = build_interpreter(args)

    if args.cmd == "reply":
        result = interp.interpret(args.text)
        if args.trace:
            print(f"notes: {result.notes}")
            print(f"reply: {result.reply}")
        else:
            print(result.reply)
        return 0

    if args.cmd == "gui":
        return _run_gui(interp)

    print("cni repl. :q to quit")
    show_trace = False
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in {":q", ":quit", ":exit"}:
            return 0
        if line.startswith(":trace"):
            show_trace = "off" not in line
            print("trace", "on" if show_trace else "off")
            continue
        result = interp.interpret(line)
        if show_trace:
            print(f"notes: {result.notes}")
            print(f"reply: {result.reply}")
        else:
            print(result.reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
