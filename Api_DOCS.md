# API Documentation for Flask Voting System

All endpoints require JSON format for request bodies and respond with JSON.

---

## Authentication

### POST `/register`

Register a new voter.

- **Body**:

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "secret"
}
```

- **Returns**: `201 Created` on success

---

### POST `/login`

Authenticate voter and get JWT token.

- **Body**:

```json
{
  "email": "john@example.com",
  "password": "secret"
}
```

- **Returns**: `200 OK` with token

---

### POST `/admin/login`

Authenticate admin and get JWT token.

- **Body**:

```json
{
  "email": "admin@example.com",
  "password": "adminpass"
}
```

- **Returns**: `200 OK` with token

---

## Voting

### GET `/positions`

Returns available positions for active election.

- **Headers**: `Authorization: Bearer <token>`
- **Returns**: List of positions

---

### GET `/candidates?election_id=&position_id=`

Returns candidates for an election or position.

- **Headers**: `Authorization: Bearer <token>`
- **Returns**: List of candidates

---

### POST `/vote`

Submit a vote.

- **Headers**: `Authorization: Bearer <token>`
- **Body**:

```json
{
  "election_id": 1,
  "position_id": 2,
  "candidate_id": 5
}
```

- **Returns**: `201 Created` or error if already voted or voting is closed

---

## Admin Routes

(Require admin token)

### GET `/admin/elections`

Get all elections.

---

### POST `/admin/elections`

Create new election.

- **Body**:

```json
{
  "title": "2025 Council Elections",
  "description": "Student leadership",
  "start_time": "2025-09-01 09:00:00",
  "end_time": "2025-09-01 17:00:00"
}
```

---

### GET `/admin/elections/<id>`

Get details of an election (positions + candidates).

---

### PUT `/admin/elections/<id>`

Edit election times or description.

---

### DELETE `/admin/elections/<id>`

Delete an election.

---

### POST `/admin/elections/<id>/positions`

Add position to an election.

- **Body**:

```json
{
  "name": "President"
}
```

---

### POST `/admin/elections/<id>/candidates`

Add candidate to a position.

- **Body**:

```json
{
  "name": "Alice",
  "position_id": 3
}
```

---

### GET `/admin/elections/<id>/results`

Get results grouped by position.

---

### GET `/admin/voters`

View all registered voters.

---

### POST `/promote_user`

Promote a user to admin or other roles.

- **Headers**: `Authorization: Bearer <admin_token>`
- **Body**:

```json
{
  "email": "user@example.com",
  "role": "admin"
}
```

---

### POST `/admin/sessions`

Create a voting session.

- **Body**:

```json
{
  "election_id": 1,
  "start_time": "2025-09-01 09:00:00",
  "end_time": "2025-09-01 17:00:00"
}
```

---

### GET `/results?election_id=1&position_id=2`

Public route to get results (authorized).

---

## Notes

- All `datetime` fields are in `YYYY-MM-DD HH:MM:SS` format (24-hr)
- Timezone used: `Africa/Nairobi`
- JWT token is required in the `Authorization` header for protected routes
