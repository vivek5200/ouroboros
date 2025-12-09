---
layout: home
title: Home
nav_order: 1
---

# Ouroboros
{: .fs-9 }

**AI-powered code refactoring system**
{: .fs-6 .fw-300 }

[Get Started](./PHASE2_DOCUMENTATION){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 } [View on GitHub](https://github.com/vivek5200/ouroboros){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## Project Overview

Ouroboros is an autonomous agent designed to self-correct and refactor codebases. It utilizes advanced LLM integration to analyze project structure and implement optimizations.

### Key Features

* **⚡ Automated Refactoring**: Intelligent code analysis.
* **🧠 LLM Integration**: 6 providers + AI21 Jamba (256k context).
* **🔄 Self-Healing**: Detects errors and proposes fixes iteratively.
* **🚀 Deep Context**: AI21 Cloud integration for massive codebases.

### Documentation Status

| Module | Status | Description |
|:-------|:-------|:------------|
| **Phase 1** | ✅ Complete | Code parsing and graph database construction. |
| **Phase 2** | ✅ Complete | LLM-powered refactor plan generation with 6 providers. |
| **Phase 3** | ✅ Complete | Jamba context encoder with 256k token window (AI21 Cloud). |

---

### Installation

```bash
git clone https://github.com/vivek5200/ouroboros.git
cd ouroboros
pip install -r requirements.txt