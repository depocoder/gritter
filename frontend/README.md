# Gritter Frontend

Frontend of the Gritter social network: React + TypeScript + Vite, served by Nginx in Docker. The design is ported from the team's HTML/CSS mockup ([grit-front-sandbox](https://github.com/Echidden/grit-front-sandbox)).

## Running

### Development (local backend)

```bash
# from the repository root — start the backend
docker compose up -d api db redis rmq minio migrator

cd frontend
npm install
npm run dev          # http://localhost:5173, /api is proxied to localhost:8000
```

To develop against the team's production server:

```bash
VITE_API_TARGET=https://gritter.azamaton.ru npm run dev
```

### Production (Docker + Nginx)

```bash
# frontend + the whole backend locally
docker compose up -d --build
# frontend: http://localhost:8080 (override with FRONTEND_PORT)

# frontend against the production backend
FRONTEND_BACKEND_URL=https://gritter.azamaton.ru docker compose up -d --build frontend
```

The build is two-staged (`frontend/Dockerfile`): `node:22-alpine` builds the Vite bundle → `nginx:1.27-alpine` serves the static files and proxies `/api` to the backend (`nginx.conf.template`, target set via the `BACKEND_URL` env variable). The app always calls its own origin, so the backend needs no CORS setup.

### Tests

```bash
npm test             # vitest, 30 tests
```

## Architecture — Feature-Sliced Design (FSD)

The code is split into layers with imports going strictly downwards
(`app → pages → widgets → features → entities → shared`); each slice exposes
its public API through an `index.ts`:

```
src/
├── app/        router (lazy routes), layout, ProtectedRoute, global styles and tokens
├── pages/      screens: login, feed, profile, profile-other
├── widgets/    header (lives in the layout — survives navigation)
├── features/   auth, like, comment, follow, create-post, upload-avatar
├── entities/   user, post, comment — types (mirroring backend pydantic schemas), api, UI
└── shared/     ui kit (Button, Input, Avatar, Spinner), api client, config, utils
```

Design tokens from the mockup (colors, fonts, radii) are CSS variables in
`src/app/styles/tokens.css`; components never hardcode values.

### Auth flow

JWT pair: access (15 min) + single-use refresh (7 days). `shared/api/client.ts`
attaches `Authorization: Bearer`, transparently refreshes the pair once on 401
and retries the request; concurrent 401s share a single refresh request.
Tokens live in localStorage (a deliberate trade-off for this project: survives
reloads, but is readable from JS).

## Rendering optimizations

- **Code splitting**: pages are wired through `React.lazy` + `Suspense` —
  each screen ships as its own chunk (`login` ~1 KB, `feed` ~11 KB, separate
  from the vendor bundle).
- **`memo` on `PostCard`**: liking one post does not re-render its siblings —
  props are primitives and callbacks are stabilized with `useCallback`.
- **Optimistic likes** (`features/like`): the UI updates instantly, the counter
  re-syncs with the server reply, and rolls back on error.
- **Lazy comments**: the comments section mounts (and fetches) only when a
  card is expanded.
- **Pagination** instead of loading the whole feed ("Show more", `has_next`
  from the API).
- **Persistent shell**: the Header lives in a layout route and survives
  navigation.
- `useMemo` for derived lists, stable `key`s by id.

## Tests (Vitest + React Testing Library)

| What | Where | Scenarios |
|---|---|---|
| Business validation | `features/auth/lib/validation.test.ts` | boundaries: password 7/8 chars, login 2/3/33, empty and whitespace-only fields |
| API client | `shared/api/client.test.ts` | token attachment, 401 → refresh → retry, dead refresh → logout, FastAPI errors, 204 |
| Optimistic like | `features/like/model/useLikes.test.tsx` | instant update, server re-sync, rollback on error, persistence |
| Comment counters | `features/comment/model/useCommentCounts.test.tsx` | snapshot vs API total re-sync, increment, per-post independence |
| Register form | `features/auth/ui/RegisterForm.test.tsx` | errors before any request, short password, valid submit hits the API |
| Post card | `entities/post/ui/PostCard.test.tsx` | data rendering, like callback, conditional follow button, lazy comments |

## Known API limitations (and workarounds)

- No `GET /users/{id}/profile` — another user's profile is built from their
  posts (`GET /posts?author_id=X`; `PostOut` embeds the author).
- No "liked by me" / "following" flags — client state is kept in localStorage
  per user and reconciled with API replies (409/404).
- The following feed (`/users/me/feed`) returns posts without the author and
  counters — its cards are reduced and link to the author's profile.
- No search: it is P3 in the user stories (out of MVP), so the mockup's search
  box was not ported. "Forgot password" is a demo, as in the mockup.
- `post.comments_count` is a denormalized snapshot; once the comments section
  loads, the badge re-syncs with the real total (`useCommentCounts`).
- A new post goes to moderation (transactional outbox + GigaChat worker) —
  the frontend shows `moderation_message`, and the post appears in the feed
  once published.
