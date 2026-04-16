# Project Knowledge Item: Environment & Protocol Locking

## 1. Environment Anchor
- **CRITICAL**: This project MUST use `.venv` (with a dot). 
- **FORBIDDEN**: Do not use `venv`.
- **Reason**: All PaddleOCR and specialized heavy dependencies are installed exclusively in `.venv`.

## 2. API Contract (V3.0+)
- **ROOT KEY**: All audit responses MUST wrap result in `{"status": "completed", "report": {...}}`.
- **Reason**: Frontend `app.js` strictly validates this top-level `status` key to handle loading states and modal transitions.

## 3. Encoding Standard
- **MODE**: Always use `ensure_ascii=False` for `json.dumps`.
- **Reason**: Prevents Chinese character corruption and Unicode emoji (checkmarks) from crashing the parser.
