---
title: Developer laptop setup - Python and uv
category: Software
tags: developer, python, uv, setup
status: draft
visibility: public
owner: bob
---
Developers can request the **Developer** device profile, which allows installing development tools without a software request.

## Python

Use **uv** to install and manage Python versions. Don't use the Python installer from python.org.

```
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
```

## Projects

- Create projects with `uv init` and add dependencies with `uv add`.
- Never commit `.env` files or API keys. Secrets go in the vault; see the security team's guide.

TODO: add the internal package index URL and vault instructions before publishing.
