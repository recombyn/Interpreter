# Architecture

Pipeline:

```
input → E → user_dict(Table 2) → F41–50 → G → I(Table 1) → D → kernel(RO/WC/QP/MEM/REN) → output
```

```
User input
    │
    ▼
┌─────────── RO routing ───────────┐
│  教/记住/学习/记 or teach?        │
│   yes → hear (write)  no → turn (read)│
└──────────────┬───────────────────┘
               ▼
┌─────────── Preprocess ───────────┐
│  E → user_dict → F41–50 → G → I  │
│  I hit → spoken reply, stop      │
└──────────────┬───────────────────┘
               ▼
┌─────────── D decode ─────────────┐
│  D66/D67 literal early-exit; else lex+D│
│  write tell / read find·yesno    │
└──────────────┬───────────────────┘
               ▼
┌─────────── World ────────────────┐
│  isa / located / has / event…    │
│  inference depth ≤ 2             │
└──────────────┬───────────────────┘
               ▼
┌─────────── REN output ───────────┐
│  form/lex → NL                   │
│  REN1 bare surface; REN2 empty phrase│
└──────────────────────────────────┘
```


## Fact shape

```text
isa(电脑, 机器)
located(电脑, 桌上)          # native predicate
has(我, 电脑)                # native predicate
of(kind, e.1, invent)        # event roles still use of
of(content, 静夜思, 床前明月光)
```
