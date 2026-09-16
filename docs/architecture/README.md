# Azure Target Architecture

The editable [Draw.io architecture](acacium-azure-solution-architecture.drawio) is the production
target for this local prototype. It deliberately separates the operational demo boundary from Azure
services that are not available for the interview proof of concept.

| Local prototype | Azure target | Responsibility |
|---|---|---|
| React/Vite client | Azure Static Web Apps | Evidence-first shortlist and reviewer experience |
| FastAPI API | Azure Container Apps | API, policy enforcement and OpenAPI contract |
| Local deterministic extractor | Container Apps Job / Azure Functions | PDF parsing, structured extraction and validation |
| Local SQLite review database | Azure SQL Database | Run, evidence, revision and review history |
| Local files under `data/` | Azure Blob Storage | Immutable originals and derived page artefacts |
| Local PDF parser | Azure AI Document Intelligence | Managed layout/OCR adapter when approved |
| Recorded/local extraction | Azure AI Foundry | Governed model adapter with versioned prompt/schema |
| Local application logs | Azure Monitor / Application Insights | Correlation, audit and operational alerts |

The code intentionally uses local adapter boundaries and does not include unused Azure SDK stubs.
That keeps the proof of concept runnable without cloud credentials while leaving each deployment
replacement explicit and testable.
