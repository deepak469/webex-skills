# Knowledge API contract

## Service origin

The helper uses the single service origin defined in `scripts/webex-knowledge.mjs`. The released origin must use HTTPS. To test against a local service in a development checkout, edit that constant; do not distribute that edited package.

## Search

`POST /webex-developer-ai-assistant/api/v1/knowledge/search`

Request:

```json
{
  "queries": ["How do I create a Webex meeting using the REST API?"],
  "sources": ["docs", "api"],
  "filter": "webex_suite",
  "max_results_per_source": 5
}
```

Constraints:

- `queries`: 1–8 distinct, non-empty strings; maximum 500 characters each.
- `sources`: one or both of `docs` and `api`; defaults to both.
- `filter`: optional `webex_suite` or `cc`.
- `max_results_per_source`: integer from 1–10; defaults to 5.

Response:

```json
{
  "tracking_id": "DEV-AI-ASSIST_...",
  "results": [
    {
      "query": "...",
      "records": [
        {
          "record_id": "...",
          "source_type": "docs",
          "document_id": "...",
          "title": "...",
          "content": "...",
          "source_url": "https://...",
          "score": 0.9,
          "metadata": {}
        }
      ],
      "partial": false,
      "warnings": []
    }
  ],
  "partial": false
}
```

## Authentication helper

The helper implements these endpoints without exposing tokens to the agent:

- `POST /webex-developer-ai-assistant/api/v1/auth/webex/sessions`
- `POST /webex-developer-ai-assistant/api/v1/auth/webex/sessions/{session_id}/token`
- `POST /webex-developer-ai-assistant/api/v1/auth/webex/token/refresh`

The browser login handoff uses `X25519-HKDF-SHA256-AESGCM`. The ephemeral client private key stays in helper memory. Tokens are stored in macOS Keychain or encrypted with Windows DPAPI for the current user.

## Failure handling

- `401`: the helper refreshes once, then starts a new login if the refresh token is invalid.
- `403` with `Not supported`: the knowledge surface is disabled in that deployment.
- `422`: fix the request; do not retry unchanged.
- `503`: report that grounded Webex knowledge is temporarily unavailable.
- `partial: true`: use available records and disclose the missing source/query coverage.

The helper retries authentication, not arbitrary search failures. It performs at most one search retry after refreshing or replacing an invalid access token.
