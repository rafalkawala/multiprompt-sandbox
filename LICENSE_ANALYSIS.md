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

| Package | Version | License | Link | Risk & Assessment |
| :--- | :--- | :--- | :--- | :--- |
| aiohttp | 3.9.1 | Apache 2.0 | [Link](https://github.com/aio-libs/aiohttp) | **OK (Low Risk)**<br>Requires attribution. |
| aiosignal | 1.4.0 | Apache 2.0 | [Link](https://github.com/aio-libs/aiosignal) | **OK (Low Risk)**<br>Requires attribution. |
| alembic | 1.13.1 | MIT | [Link](https://alembic.sqlalchemy.org) | **OK (Low Risk)**<br>Requires attribution. |
| anyio | 4.12.1 | MIT | [Link](https://anyio.readthedocs.io/en/stable/versionhistory.html) | **OK (Low Risk)**<br>Requires attribution. |
| authlib | 1.6.0 | BSD 3-Clause | [Link](https://github.com/authlib/authlib) | **OK (Low Risk)**<br>Requires attribution. |
| bcrypt | 5.0.0 | Apache 2.0 | [Link](https://github.com/pyca/bcrypt/) | **OK (Low Risk)**<br>Requires attribution. |
| cachetools | 5.5.2 | MIT | [Link](https://github.com/tkem/cachetools/) | **OK (Low Risk)**<br>Requires attribution. |
| certifi | 2026.1.4 | MPL 2.0 | [Link](https://github.com/certifi/python-certifi) | **OK (Low/Medium Risk)**<br>Weak Copyleft. Attribution required. Source code of *modified* files must be disclosed (unlikely if used as-is). |
| cffi | 2.0.0 | MIT | [Link](https://cffi.readthedocs.io/en/latest/whatsnew.html) | **OK (Low Risk)**<br>Requires attribution. |
| click | 8.3.1 | BSD 3-Clause | [Link](https://github.com/pallets/click/) | **OK (Low Risk)**<br>Requires attribution. |
| cryptography | 46.0.3 | Apache 2.0 OR BSD 3-Clause | [Link](https://github.com/pyca/cryptography) | **OK (Low Risk)**<br>Requires attribution. |
| dnspython | 2.8.0 | ISC | [Link](https://www.dnspython.org) | **OK (Low Risk)**<br>Requires attribution. |
| email-validator | 2.1.0 | CC0 1.0 (Public Domain) | [Link](https://github.com/JoshData/python-email-validator) | **OK (No Risk)**<br>No attribution required (but recommended). |
| fastapi | 0.109.0 | MIT | [Link](https://github.com/tiangolo/fastapi) | **OK (Low Risk)**<br>Requires attribution. |
| google-ai-generativelanguage | 0.6.6 | Apache 2.0 | [Link](https://github.com/googleapis/google-cloud-python/tree/main/packages/google-ai-generativelanguage) | **OK (Low Risk)**<br>Requires attribution. |
| google-auth | 2.27.0 | Apache 2.0 | [Link](https://github.com/googleapis/google-auth-library-python) | **OK (Low Risk)**<br>Requires attribution. |
| google-cloud-aiplatform | 1.71.0 | Apache 2.0 | [Link](https://github.com/googleapis/python-aiplatform) | **OK (Low Risk)**<br>Requires attribution. |
| google-cloud-storage | 2.14.0 | Apache 2.0 | [Link](https://github.com/googleapis/python-storage) | **OK (Low Risk)**<br>Requires attribution. |
| google-cloud-tasks | 2.14.2 | Apache 2.0 | [Link](https://github.com/googleapis/python-tasks) | **OK (Low Risk)**<br>Requires attribution. |
| google-generativeai | 0.7.2 | Apache 2.0 | [Link](https://github.com/google/generative-ai-python) | **OK (Low Risk)**<br>Requires attribution. |
| grpcio | 1.76.0 | Apache 2.0 | [Link](https://grpc.io) | **OK (Low Risk)**<br>Requires attribution. |
| httpcore | 1.0.9 | BSD 3-Clause | [Link](https://github.com/encode/httpcore) | **OK (Low Risk)**<br>Requires attribution. |
| httpx | 0.26.0 | BSD 3-Clause | [Link](https://github.com/encode/httpx) | **OK (Low Risk)**<br>Requires attribution. |
| itsdangerous | 2.1.0 | BSD 3-Clause | [Link](https://github.com/pallets/itsdangerous/) | **OK (Low Risk)**<br>Requires attribution. |
| langchain | 0.3.0 | MIT | [Link](https://github.com/langchain-ai/langchain) | **OK (Low Risk)**<br>Requires attribution. |
| langchain-community | 0.3.0 | MIT | [Link](https://github.com/langchain-ai/langchain) | **OK (Low Risk)**<br>Requires attribution. |
| langchain-core | 0.3.63 | MIT | [Link](https://github.com/langchain-ai/langchain) | **OK (Low Risk)**<br>Requires attribution. |
| langchain-google-genai | 2.0.0 | MIT | [Link](https://github.com/langchain-ai/langchain) | **OK (Low Risk)**<br>Requires attribution. |
| langgraph | 0.3.0 | MIT | [Link](https://github.com/langchain-ai/langgraph) | **OK (Low Risk)**<br>Requires attribution. |
| numpy | 1.26.4 | BSD 3-Clause | [Link](https://numpy.org) | **OK (Low Risk)**<br>Requires attribution. |
| packaging | 24.2 | Apache 2.0 / BSD | [Link](https://github.com/pypa/packaging) | **OK (Low Risk)**<br>Requires attribution. |
| pandas | 2.1.4 | BSD 3-Clause | [Link](https://pandas.pydata.org) | **OK (Low Risk)**<br>Requires attribution. |
| passlib | 1.7.4 | BSD | [Link](https://passlib.readthedocs.io) | **OK (Low Risk)**<br>Requires attribution. |
| pgvector | 0.3.6 | MIT | [Link](https://github.com/pgvector/pgvector-python) | **OK (Low Risk)**<br>Requires attribution. |
| Pillow | 10.4.0 | HPND (MIT-like) | [Link](https://python-pillow.org) | **OK (Low Risk)**<br>Requires attribution. |
| psycopg2-binary | 2.9.9 | LGPL | [Link](https://psycopg.org/) | **Conditional (Medium Risk)**<br>Weak Copyleft. Must ensure dynamic linking (user can replace library). Attribution required. |
| pydantic | 2.9.0 | MIT | [Link](https://github.com/pydantic/pydantic) | **OK (Low Risk)**<br>Requires attribution. |
| pydantic-settings | 2.5.0 | MIT | [Link](https://github.com/pydantic/pydantic-settings) | **OK (Low Risk)**<br>Requires attribution. |
| python-dateutil | 2.9.0 | Apache 2.0 / BSD | [Link](https://github.com/dateutil/dateutil) | **OK (Low Risk)**<br>Requires attribution. |
| python-dotenv | 1.0.0 | BSD | [Link](https://github.com/theskumar/python-dotenv) | **OK (Low Risk)**<br>Requires attribution. |
| python-jose | 3.3.0 | MIT | [Link](http://github.com/mpdavis/python-jose) | **OK (Low Risk)**<br>Requires attribution. |
| python-multipart | 0.0.6 | Apache 2.0 | [Link](https://github.com/andrew-d/python-multipart) | **OK (Low Risk)**<br>Requires attribution. |
| PyYAML | 6.0.1 | MIT | [Link](https://pyyaml.org/) | **OK (Low Risk)**<br>Requires attribution. |
| regex | 2025.11.3 | Apache 2.0 | [Link](https://github.com/mrabarnett/mrab-regex) | **OK (Low Risk)**<br>Requires attribution. |
| requests | 2.32.5 | Apache 2.0 | [Link](https://requests.readthedocs.io) | **OK (Low Risk)**<br>Requires attribution. |
| sqlalchemy | 2.0.25 | MIT | [Link](https://www.sqlalchemy.org) | **OK (Low Risk)**<br>Requires attribution. |
| starlette | 0.35.1 | BSD 3-Clause | [Link](https://github.com/encode/starlette) | **OK (Low Risk)**<br>Requires attribution. |
| structlog | 25.5.0 | MIT / Apache 2.0 | [Link](https://github.com/hynek/structlog) | **OK (Low Risk)**<br>Requires attribution. |
| tenacity | 8.2.3 | Apache 2.0 | [Link](https://github.com/jd/tenacity) | **OK (Low Risk)**<br>Requires attribution. |
| tiktoken | 0.7.0 | MIT | [Link](https://github.com/openai/tiktoken) | **OK (Low Risk)**<br>Requires attribution. |
| typing-extensions | 4.15.0 | PSF 2.0 | [Link](https://github.com/python/typing_extensions) | **OK (Low Risk)**<br>Requires attribution. |
| urllib3 | 2.6.3 | MIT | [Link](https://github.com/urllib3/urllib3) | **OK (Low Risk)**<br>Requires attribution. |
| uvicorn | 0.37.0 | BSD 3-Clause | [Link](https://uvicorn.dev/) | **OK (Low Risk)**<br>Requires attribution. |
| uvloop | 0.22.1 | MIT / Apache 2.0 | [Link](https://github.com/MagicStack/uvloop) | **OK (Low Risk)**<br>Requires attribution. |
| watchfiles | 1.1.1 | MIT | [Link](https://github.com/samuelcolvin/watchfiles) | **OK (Low Risk)**<br>Requires attribution. |
| websockets | 16.0 | BSD 3-Clause | [Link](https://github.com/python-websockets/websockets) | **OK (Low Risk)**<br>Requires attribution. |
| yarl | 1.22.0 | Apache 2.0 | [Link](https://github.com/aio-libs/yarl) | **OK (Low Risk)**<br>Requires attribution. |

*Note: Dependencies of dependencies (transitive) are generally covered by similar permissive licenses in the Python ecosystem, but a full scan of the `site-packages` is recommended for legal certification.*

### Frontend (Angular/NPM)

| Package | License | Link | Risk & Assessment |
| :--- | :--- | :--- | :--- |
| @angular/* (core, common, etc.) | MIT | [Link](https://github.com/angular/angular/blob/main/LICENSE) | **OK (Low Risk)**<br>Requires attribution. |
| rxjs | Apache 2.0 | [Link](https://github.com/ReactiveX/rxjs/blob/master/LICENSE.txt) | **OK (Low Risk)**<br>Requires attribution. |
| tslib | 0BSD | [Link](https://github.com/microsoft/tslib/blob/master/LICENSE.txt) | **OK (No Risk)**<br>Attribution often not strictly required but recommended. |
| zone.js | MIT | [Link](https://github.com/angular/angular/blob/main/packages/zone.js/LICENSE) | **OK (Low Risk)**<br>Requires attribution. |

## Commercial Strategy: Selling vs. SaaS

This section details the specific requirements for two common business models: **Selling** the software (distribution) and operating it as a **SaaS** platform.

### 1. Selling Proprietary Licenses (On-Premise / Downloadable)
In this model, you distribute the software binary or source code to the customer.

*   **Attribution (Required):** You must include the `ThirdPartyNotices.txt` file (as described below) in the root of the delivered artifact (ZIP, ISO, Docker image).
*   **EULA Terms for LGPL:**
    *   Since you are using `psycopg2-binary` (LGPL), your End User License Agreement (EULA) **cannot** forbid the customer from reverse-engineering the software *specifically for the purpose of debugging modifications to the LGPL library*.
    *   You must allow the user to replace the LGPL component (e.g., swapping the `.so` or `.dll` file).
*   **Technical Requirement:**
    *   **Do NOT** use "single-file" compilation tools (like PyInstaller `--onefile`) that merge the Python interpreter, your code, and `psycopg2` into a single inseparable binary blob. This makes it impossible for the user to replace the LGPL library.
    *   **DO** distribute as a directory of files, a Docker container, or a standard Python virtual environment.
*   **MPL Components:**
    *   For `certifi` (MPL 2.0), if you have modified the source code of the library itself, you must provide the source code of those modifications. If you use it as-is (standard pip install), no extra action is needed beyond attribution.

### 2. Operating as SaaS (Software as a Service)
In this model, you host the software, and customers access it via the web. You do *not* send the backend code to the customer.

*   **Reduced Backend Risk:**
    *   LGPL (and GPL) generally trigger requirements upon *distribution* (conveying) of the binary. Since the backend code remains on your servers, you are not "distributing" `psycopg2-binary` to the client. Therefore, the relinking/replacement requirements **do not apply** to the backend in a pure SaaS model.
    *   *Note on AGPL:* Since there are **no AGPL** components, you are free from the "ASP Loophole" provision. You do *not* need to share your backend source code even if you modify these libraries.
*   **Frontend Distribution is Still Distribution:**
    *   The **Angular Frontend** (JavaScript/WASM) *is* downloaded to the user's browser. This constitutes distribution.
    *   **Requirement:** You **must** ensure that license headers in the JavaScript files are preserved (often handled by the build tool) or that the "Legal/About" screen in the UI is accessible to the user.
*   **Verdict:** SaaS is the path of least resistance for this stack, as it mitigates the complexities of the LGPL backend library.

## How and Where to Add Attribution

To comply with the "Attribution" requirement common to MIT, BSD, and Apache 2.0 licenses, you must include the full text of the licenses and copyright notices for all third-party software used in your application.

### 1. Create a `NOTICE` or `CREDITS` File
Compile a single text file (e.g., `NOTICE.txt`, `ThirdPartyNotices.txt`, or `CREDITS.md`) that lists each component and its license.

**Example Format:**

```text
This software includes the following third-party components:

-------------------------------------------------------------------
Component: FastAPI
License: MIT
Copyright (c) 2018 Sebastián Ramírez

Permission is hereby granted, free of charge, to any person obtaining a copy...
[Full License Text]
-------------------------------------------------------------------
Component: Angular
License: MIT
Copyright (c) 2010-2024 Google LLC.

Permission is hereby granted, free of charge...
[Full License Text]
-------------------------------------------------------------------
```

### 2. Include in Distribution
*   **Source/Binary Distribution:** Place this file in the root directory of your distribution package (zip, docker image, installer).
*   **Documentation:** Mention the use of open-source software in your user manual or EULA.

### 3. Display in User Interface (Frontend)
For a web application like this one, it is standard practice to make this information accessible within the application itself.

*   **"About" Screen:** Add an "About" or "Legal" page in the application settings or footer.
*   **Link to File:** Provide a link to the `ThirdPartyNotices.txt` file hosted on your server.
*   **UI Example:**
    > "This application is built using open-source software. [View Licenses]"

### 4. Special Handling for LGPL (psycopg2-binary)
If you continue to use `psycopg2-binary`:
*   **Dynamic Linking:** Ensure the library is not statically linked (merged) into a single executable file with your application code. If you use tools like PyInstaller, use `--onedir` mode (folder distribution) rather than `--onefile`, or ensure the `.so` / `.dll` files remain separate.
*   **Relinking:** The user must theoretically be able to swap the `psycopg2` library file with a newer or modified version.

## Perspective on Proprietary Distribution

You **can** generally distribute this software as a proprietary product, provided you adhere to the attribution requirements of the identified licenses.

1.  **Attribution is Key:** Most of these licenses (MIT, BSD, Apache 2.0) require that you include the original copyright notice and license text in your distribution (e.g., in a "Credits" or "Legal" screen, or a text file accompanying the software).
2.  **No "Copyleft" Blocks:** There are no AGPL (Affero GPL) or GPL libraries in the direct dependencies list. This means you are not compelled to release your own source code just because you use these libraries.
3.  **LGPL Warning (psycopg2-binary):** The `psycopg2-binary` package is LGPL.
    *   *Constraint:* You must allow the user to replace this library with their own version.
    *   *Solution:* In a Python environment, this is usually satisfied because the libraries are dynamically loaded/interpreted (files are separate). Do not compile everything into a single inseparable binary blob (like with PyInstaller's strict "onefile" mode without care) if you want to be perfectly safe, though even then, there are workarounds.
    *   *Alternative:* If strict proprietary control is needed without this "replacement" clause, consider switching to `asyncpg` (Apache 2.0).

## Proposed Proprietary License (Draft)

**IMPORTANT DISCLAIMER:** *The following is a draft template provided by an AI assistant and does NOT constitute legal advice. You must have this document reviewed and finalized by a qualified attorney in your jurisdiction to ensure it effectively protects your rights and complies with all applicable laws.*

---

### END USER LICENSE AGREEMENT (EULA)

This End User License Agreement ("Agreement") is a legal agreement between you ("Licensee" or "You") and [Your Company Name] ("Licensor") for the [Software Name] software product, which includes computer software and may include associated media, printed materials, and "online" or electronic documentation ("Software").

**1. GRANT OF LICENSE**
Subject to the terms of this Agreement, Licensor grants to you a non-exclusive, non-transferable, limited license to install and use the Software solely for your internal business purposes. All rights not expressly granted to you are reserved by Licensor.

**2. COPYRIGHT AND OWNERSHIP**
The Software is protected by copyright laws and international copyright treaties, as well as other intellectual property laws and treaties. The Software is licensed, not sold. Title, ownership rights, and intellectual property rights in and to the Software shall remain with Licensor.

**3. RESTRICTIONS**
You may not:
*   (a) Copy the Software, except for a reasonable number of copies for backup or archival purposes.
*   (b) Modify, translate, adapt, or create derivative works from the Software.
*   (c) Distribute, rent, lease, lend, sell, or sublicense the Software to any third party.
*   (d) Remove any proprietary notices, labels, or marks from the Software.

**4. REVERSE ENGINEERING**
You acknowledge that the Software contains trade secrets of Licensor. You agree not to reverse engineer, decompile, disassemble, or attempt to derive the source code of the Software, except and only to the extent that such activity is expressly permitted by applicable law notwithstanding this limitation.
*   **LGPL Exception:** Notwithstanding the foregoing, if any component of the Software is licensed under the GNU Lesser General Public License ("LGPL"), you may reverse engineer the Software solely to the extent necessary to debug your modifications to such LGPL-licensed component, as required by the terms of the LGPL.

**5. THIRD-PARTY SOFTWARE**
The Software may contain or be accompanied by third-party software, including open-source software, which is subject to its own license terms. These terms are provided in the `NOTICE.txt` file (or equivalent) accompanying the Software. Your use of such third-party software is governed by the applicable third-party license terms, and nothing in this Agreement limits your rights under, or grants you rights that supersede, the terms and conditions of any applicable third-party license.

**6. DISCLAIMER OF WARRANTY**
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. LICENSOR DOES NOT WARRANT THAT THE FUNCTIONS CONTAINED IN THE SOFTWARE WILL MEET YOUR REQUIREMENTS OR THAT THE OPERATION OF THE SOFTWARE WILL BE UNINTERRUPTED OR ERROR-FREE.

**7. LIMITATION OF LIABILITY**
IN NO EVENT SHALL LICENSOR BE LIABLE FOR ANY DAMAGES WHATSOEVER (INCLUDING, WITHOUT LIMITATION, DAMAGES FOR LOSS OF BUSINESS PROFITS, BUSINESS INTERRUPTION, LOSS OF BUSINESS INFORMATION, OR ANY OTHER PECUNIARY LOSS) ARISING OUT OF THE USE OF OR INABILITY TO USE THE SOFTWARE, EVEN IF LICENSOR HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

**8. TERMINATION**
This Agreement is effective until terminated. Your rights under this Agreement will terminate automatically without notice from Licensor if you fail to comply with any term(s) of this Agreement. Upon termination, you shall cease all use of the Software and destroy all copies, full or partial, of the Software.

**9. GOVERNING LAW**
This Agreement shall be governed by and construed in accordance with the laws of [Your State/Country].

**Disclaimer:** *I am an AI assistant, not a lawyer. This analysis is based on metadata provided by the package registries. For a commercial product launch, you should consult with legal counsel to verify compliance.*
