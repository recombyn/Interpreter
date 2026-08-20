# CNI Docs

Vite + React docs site (same pattern as [recombyn/docs](https://github.com/recombyn/docs)).

| | |
|--|--|
| Source | this folder |
| Live | https://recombyn.github.io/concept-network-interpreter/ |

## Local

```bash
cd docs
npm install
npm run dev
```

http://localhost:5175

## Languages

- `content/zh-CN/` — 简体中文
- `content/en/` — English

## Deploy

Push to `main` (or run **Deploy Docs** workflow). CI builds with
`VITE_DOCS_BASE=/concept-network-interpreter/` and publishes `dist` to the
`gh-pages` branch of this repo.

GitHub → Settings → Pages → Source: **Deploy from a branch** → `gh-pages` / `/ (root)`.
