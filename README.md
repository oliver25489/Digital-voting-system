markdown name=README.md
# Flask Voting System Backend

A simple digital voting system backend with user roles, JWT authentication, and admin management.

## Features

- Voter registration & authentication
- Role-based access control (admin, voter)
- Election, candidate, position, voting session management
- Secure voting and audit logs
- Cast votes securely with validation
- View results by election and position
- Admin management of users, elections, and sessions
- Timezone-aware (Africa/Nairobi)
- REST API endpoints with CORS support

## Setup

1. **Clone repository**
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment**
   - Create a `.env` file with:
     ```
     DATABASE_URL=sqlite:///voting.db
     JWT_SECRET_KEY=your-secret-key
     ```
4. **Migrate database**
   ```bash
   flask db upgrade
   ```
5. **Run app**
   ```bash
   flask run
   ```

## API 

See [API_DOCS.md](Api_DOCS.md) for detailed endpoints.

## Testing

Run tests with:
```bash
pytest
```
or
```bash
python -m unittest discover
```

---

## License

MIT