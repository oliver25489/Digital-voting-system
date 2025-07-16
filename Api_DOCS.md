markdown name=API_DOCS.md
# Voting System API Documentation

## Authentication

### Register
- **POST** `/register`
- Request JSON: `{ "name": "string", "email": "string", "password": "string" }`
- Response: 201 Created or error message

### Login
- **POST** `/login`
- Request JSON: `{ "email": "string", "password": "string" }`
- Response: 200 OK with access_token

---

## Voting

### List Candidates
- **GET** `/candidates?election_id=&position_id=`
- Auth: JWT required
- Response: List of candidates

### Cast Vote
- **POST** `/vote`
- Auth: JWT required
- Request JSON: `{ "election_id": int, "position_id": int, "candidate_id": int }`

### Results
- **GET** `/results?election_id=&position_id=`
- Auth: JWT required

---

## Admin Endpoints

### Create Election
- **POST** `/create_election`
- Auth: Admin JWT required

### Promote User
- **POST** `/promote_user`
- Auth: Admin JWT required

### Manage Positions
- **POST** `/positions` (create)
- **PUT** `/positions/<position_id>` (update)
- **DELETE** `/positions/<position_id>` (delete)
- Auth: Admin JWT required

### Start Voting Session
- **POST** `/start_voting_session`
- Auth: Admin JWT required

### Audit Logs
- **GET** `/audit_logs`
- Auth: Admin JWT required

---

## Error Handling

- 400: Missing data, bad request
- 401: Unauthorized
- 403: Forbidden (insufficient privileges)
- 404: Not found
- 500: Internal server error

---