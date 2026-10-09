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

The helper signs in directly with Webex as a public OAuth client using Authorization Code with PKCE (S256); there is no client secret.

- Authorize: `https://idbroker.webex.com/idb/oauth2/v1/authorize` with scopes `identity:people_read spark:mcp`.
- Callback: `http://localhost:17177/callback`, served by a short-lived listener bound to `127.0.0.1` that validates `state` and closes after one callback or 5 minutes.
- Token exchange and refresh: `POST /idb/oauth2/v1/access_token` on the idbroker for the cluster encoded in the authorization code.

The knowledge service accepts the resulting Webex access token as a bearer token. Tokens are stored in macOS Keychain or encrypted with Windows DPAPI for the current user and are never printed.

## Failure handling

- `401`: the helper refreshes once, then starts a new login if the refresh token is invalid.
- `403` with `Not supported`: the knowledge surface is disabled in that deployment.
- `422`: fix the request; do not retry unchanged.
- `503`: report that grounded Webex knowledge is temporarily unavailable.
- `partial: true`: use available records and disclose the missing source/query coverage.

The helper retries authentication, not arbitrary search failures. It performs at most one search retry after refreshing or replacing an invalid access token.
