# Security Audit Summary

## Overview

This pull request provides a summary of security vulnerabilities identified in the project's dependencies for both the Frontend and Backend. No fixes have been applied; this report is for information and planning purposes only.

## Frontend (Angular)

**Vulnerabilities Found:** 14 (1 Low, 8 Moderate, 5 High)

The majority of issues appear to be transitive dependencies of `@angular-devkit/build-angular`.

### High Severity
*   **@angular/compiler** (via `@angular-devkit/build-angular`) - [GHSA-v4hv-rgfq-gp49](https://github.com/advisories/GHSA-v4hv-rgfq-gp49)

### Moderate Severity
*   **esbuild** (<=0.24.2)
    *   Issue: Enables requests to dev server to read response.
    *   Patched in: >=0.25.0
*   **http-proxy-middleware** (>=1.3.0 <2.0.9)
    *   Issue: Denial of service / potential bypass.
    *   Patched in: >=2.0.9
*   **webpack-dev-server** (<=5.2.0)
    *   Issue: Source code theft via malicious website.
    *   Patched in: >=5.2.1
*   **js-yaml**
    *   Issue: Prototype pollution.
    *   Patched in: >=3.14.2 / >=4.1.1
*   **node-forge** (<1.3.2)
    *   Issue: ASN.1 OID Integer Truncation.
    *   Patched in: >=1.3.2

### Low Severity
*   **tmp** (<=0.2.3)
    *   Issue: Arbitrary file write.
    *   Patched in: >=0.2.4

---

## Backend (Python)

**Vulnerabilities Found:** 22 known vulnerabilities in 12 packages.

### Vulnerability Details

| Package | Current Version | ID | Fix Version |
| :--- | :--- | :--- | :--- |
| **aiohttp** | 3.9.1 | PYSEC-2024-24, PYSEC-2024-26, CVE-2024-27306, CVE-2024-30251, CVE-2024-52304, CVE-2025-53643 | 3.9.2, 3.9.4, 3.10.11, 3.12.14 |
| **authlib** | 1.6.0 | CVE-2025-59420, CVE-2025-61920, CVE-2025-62706 | 1.6.4, 1.6.5 |
| **ecdsa** | 0.19.1 | CVE-2024-23342 | - |
| **fastapi** | 0.109.0 | PYSEC-2024-38 | 0.109.1 |
| **langchain** | 0.3.0 | CVE-2024-7774 | - |
| **langchain-community** | 0.3.0 | CVE-2025-6984 | 0.3.27 |
| **langchain-core** | 0.3.63 | CVE-2025-65106 | 0.3.80, 1.0.7 |
| **langchain-text-splitters** | 0.3.8 | CVE-2025-6985 | 0.3.9 |
| **langgraph-checkpoint** | 2.1.2 | CVE-2025-64439 | 3.0.0 |
| **python-jose** | 3.3.0 | PYSEC-2024-232, PYSEC-2024-233 | 3.4.0 |
| **python-multipart** | 0.0.6 | CVE-2024-24762, CVE-2024-53981 | 0.0.7, 0.0.18 |
| **starlette** | 0.35.1 | CVE-2024-47874, CVE-2025-54121 | 0.40.0, 0.47.2 |

## Observations

*   **Frontend:** The frontend dependencies, particularly the build tools (`@angular-devkit/build-angular`), are pulling in several outdated transitive dependencies with known issues. Updating Angular and its related dev-kits would likely resolve most of these.
*   **Backend:** Several core libraries like `fastapi`, `aiohttp`, `starlette` (which fastapi depends on), and `langchain` related packages are outdated and contain high-severity vulnerabilities (e.g., CVEs in `aiohttp` and `python-multipart`). A broad update of the backend requirements is recommended.
