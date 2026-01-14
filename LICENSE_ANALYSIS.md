# License Analysis for Proprietary Distribution

This document provides an analysis of the licenses for the open-source libraries and packages used in this project, specifically regarding the feasibility of deploying the software as a proprietary distribution.

## Executive Summary

The codebase primarily uses components with permissive licenses (MIT, Apache 2.0, BSD), which are generally compatible with proprietary distribution.

**Key Findings:**
*   **Permissive Core:** The vast majority of dependencies (FastAPI, Angular, LangChain, Pydantic, etc.) are under MIT or Apache 2.0 licenses, allowing for proprietary modification and redistribution without source code disclosure.
*   **LGPL Consideration:** The `psycopg2-binary` package is licensed under LGPL. While this allows for use in proprietary software, it requires that the LGPL library be replaceable by the end-user (usually satisfied by dynamic linking, which Python does by default).
    *   *Recommendation:* For a strict proprietary distribution, ensure you are not statically linking this library in a way that prevents replacement, or switch to a permissively licensed driver like `pg8000` or `asyncpg` (Apache 2.0) if LGPL compliance is a concern.
*   **No Strong Copyleft:** No GPL or AGPL libraries were identified in the primary dependencies, which would otherwise mandate source code disclosure for the entire application.

## Detailed License Table

### Backend (Python)

| Package | Version | License | Link |
| :--- | :--- | :--- | :--- |
| aiohttp | 3.9.1 | Apache 2.0 | [Link](https://github.com/aio-libs/aiohttp) |
| aiosignal | 1.4.0 | Apache 2.0 | [Link](https://github.com/aio-libs/aiosignal) |
| alembic | 1.13.1 | MIT | [Link](https://alembic.sqlalchemy.org) |
| anyio | 4.12.1 | MIT | [Link](https://anyio.readthedocs.io/en/stable/versionhistory.html) |
| authlib | 1.6.0 | BSD 3-Clause | [Link](https://github.com/authlib/authlib) |
| bcrypt | 5.0.0 | Apache 2.0 | [Link](https://github.com/pyca/bcrypt/) |
| cachetools | 5.5.2 | MIT | [Link](https://github.com/tkem/cachetools/) |
| certifi | 2026.1.4 | MPL 2.0 | [Link](https://github.com/certifi/python-certifi) |
| cffi | 2.0.0 | MIT | [Link](https://cffi.readthedocs.io/en/latest/whatsnew.html) |
| click | 8.3.1 | BSD 3-Clause | [Link](https://github.com/pallets/click/) |
| cryptography | 46.0.3 | Apache 2.0 OR BSD 3-Clause | [Link](https://github.com/pyca/cryptography) |
| dnspython | 2.8.0 | ISC | [Link](https://www.dnspython.org) |
| email-validator | 2.1.0 | CC0 1.0 (Public Domain) | [Link](https://github.com/JoshData/python-email-validator) |
| fastapi | 0.109.0 | MIT | [Link](https://github.com/tiangolo/fastapi) |
| google-ai-generativelanguage | 0.6.6 | Apache 2.0 | [Link](https://github.com/googleapis/google-cloud-python/tree/main/packages/google-ai-generativelanguage) |
| google-auth | 2.27.0 | Apache 2.0 | [Link](https://github.com/googleapis/google-auth-library-python) |
| google-cloud-aiplatform | 1.71.0 | Apache 2.0 | [Link](https://github.com/googleapis/python-aiplatform) |
| google-cloud-storage | 2.14.0 | Apache 2.0 | [Link](https://github.com/googleapis/python-storage) |
| google-cloud-tasks | 2.14.2 | Apache 2.0 | [Link](https://github.com/googleapis/python-tasks) |
| google-generativeai | 0.7.2 | Apache 2.0 | [Link](https://github.com/google/generative-ai-python) |
| grpcio | 1.76.0 | Apache 2.0 | [Link](https://grpc.io) |
| httpcore | 1.0.9 | BSD 3-Clause | [Link](https://github.com/encode/httpcore) |
| httpx | 0.26.0 | BSD 3-Clause | [Link](https://github.com/encode/httpx) |
| itsdangerous | 2.1.0 | BSD 3-Clause | [Link](https://github.com/pallets/itsdangerous/) |
| langchain | 0.3.0 | MIT | [Link](https://github.com/langchain-ai/langchain) |
| langchain-community | 0.3.0 | MIT | [Link](https://github.com/langchain-ai/langchain) |
| langchain-core | 0.3.63 | MIT | [Link](https://github.com/langchain-ai/langchain) |
| langchain-google-genai | 2.0.0 | MIT | [Link](https://github.com/langchain-ai/langchain) |
| langgraph | 0.3.0 | MIT | [Link](https://github.com/langchain-ai/langgraph) |
| numpy | 1.26.4 | BSD 3-Clause | [Link](https://numpy.org) |
| packaging | 24.2 | Apache 2.0 / BSD | [Link](https://github.com/pypa/packaging) |
| pandas | 2.1.4 | BSD 3-Clause | [Link](https://pandas.pydata.org) |
| passlib | 1.7.4 | BSD | [Link](https://passlib.readthedocs.io) |
| pgvector | 0.3.6 | MIT | [Link](https://github.com/pgvector/pgvector-python) |
| Pillow | 10.4.0 | HPND (MIT-like) | [Link](https://python-pillow.org) |
| psycopg2-binary | 2.9.9 | LGPL | [Link](https://psycopg.org/) |
| pydantic | 2.9.0 | MIT | [Link](https://github.com/pydantic/pydantic) |
| pydantic-settings | 2.5.0 | MIT | [Link](https://github.com/pydantic/pydantic-settings) |
| python-dateutil | 2.9.0 | Apache 2.0 / BSD | [Link](https://github.com/dateutil/dateutil) |
| python-dotenv | 1.0.0 | BSD | [Link](https://github.com/theskumar/python-dotenv) |
| python-jose | 3.3.0 | MIT | [Link](http://github.com/mpdavis/python-jose) |
| python-multipart | 0.0.6 | Apache 2.0 | [Link](https://github.com/andrew-d/python-multipart) |
| PyYAML | 6.0.1 | MIT | [Link](https://pyyaml.org/) |
| regex | 2025.11.3 | Apache 2.0 | [Link](https://github.com/mrabarnett/mrab-regex) |
| requests | 2.32.5 | Apache 2.0 | [Link](https://requests.readthedocs.io) |
| sqlalchemy | 2.0.25 | MIT | [Link](https://www.sqlalchemy.org) |
| starlette | 0.35.1 | BSD 3-Clause | [Link](https://github.com/encode/starlette) |
| structlog | 25.5.0 | MIT / Apache 2.0 | [Link](https://github.com/hynek/structlog) |
| tenacity | 8.2.3 | Apache 2.0 | [Link](https://github.com/jd/tenacity) |
| tiktoken | 0.7.0 | MIT | [Link](https://github.com/openai/tiktoken) |
| typing-extensions | 4.15.0 | PSF 2.0 | [Link](https://github.com/python/typing_extensions) |
| urllib3 | 2.6.3 | MIT | [Link](https://github.com/urllib3/urllib3) |
| uvicorn | 0.37.0 | BSD 3-Clause | [Link](https://uvicorn.dev/) |
| uvloop | 0.22.1 | MIT / Apache 2.0 | [Link](https://github.com/MagicStack/uvloop) |
| watchfiles | 1.1.1 | MIT | [Link](https://github.com/samuelcolvin/watchfiles) |
| websockets | 16.0 | BSD 3-Clause | [Link](https://github.com/python-websockets/websockets) |
| yarl | 1.22.0 | Apache 2.0 | [Link](https://github.com/aio-libs/yarl) |

*Note: Dependencies of dependencies (transitive) are generally covered by similar permissive licenses in the Python ecosystem, but a full scan of the `site-packages` is recommended for legal certification.*

### Frontend (Angular/NPM)

| Package | License | Link |
| :--- | :--- | :--- |
| @angular/* (core, common, etc.) | MIT | [Link](https://github.com/angular/angular/blob/main/LICENSE) |
| rxjs | Apache 2.0 | [Link](https://github.com/ReactiveX/rxjs/blob/master/LICENSE.txt) |
| tslib | 0BSD | [Link](https://github.com/microsoft/tslib/blob/master/LICENSE.txt) |
| zone.js | MIT | [Link](https://github.com/angular/angular/blob/main/packages/zone.js/LICENSE) |

## Perspective on Proprietary Distribution

You **can** generally distribute this software as a proprietary product, provided you adhere to the attribution requirements of the identified licenses.

1.  **Attribution is Key:** Most of these licenses (MIT, BSD, Apache 2.0) require that you include the original copyright notice and license text in your distribution (e.g., in a "Credits" or "Legal" screen, or a text file accompanying the software).
2.  **No "Copyleft" Blocks:** There are no AGPL (Affero GPL) or GPL libraries in the direct dependencies list. This means you are not compelled to release your own source code just because you use these libraries.
3.  **LGPL Warning (psycopg2-binary):** The `psycopg2-binary` package is LGPL.
    *   *Constraint:* You must allow the user to replace this library with their own version.
    *   *Solution:* In a Python environment, this is usually satisfied because the libraries are dynamically loaded/interpreted (files are separate). Do not compile everything into a single inseparable binary blob (like with PyInstaller's strict "onefile" mode without care) if you want to be perfectly safe, though even then, there are workarounds.
    *   *Alternative:* If strict proprietary control is needed without this "replacement" clause, consider switching to `asyncpg` (Apache 2.0).

**Disclaimer:** *I am an AI assistant, not a lawyer. This analysis is based on metadata provided by the package registries. For a commercial product launch, you should consult with legal counsel to verify compliance.*
