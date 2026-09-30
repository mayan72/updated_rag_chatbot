# RAG Assistant UI

React + Vite dashboard/chat UI for the current FastAPI RAG backend.

## Run

```bash
npm install
npm run dev
```

Open http://localhost:5173

Optional `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Current backend contract

POST `/chat`

```json
{"question":"What is the total sales in South India?"}
```

The UI consumes the current `type`, `answer`, `plan`, and `sources` response fields.

## Persistence

This first UI build uses browser storage only so it can run immediately. For production persistence, connect the history adapter to separate tables in the existing SQLite database:

- `chat_conversations`
- `chat_messages`

Do not mix chat records with structured RAG tables.

## Upload

The Files area is intentionally marked as future functionality. Connect it to the existing `/upload` endpoint in the next phase.
