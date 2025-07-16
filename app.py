from dotenv import load_dotenv
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from functools import wraps

def role_required(required_role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = EndUser.query.get(user_id)
            if user and user.role == required_role:
                return fn(*args, **kwargs)
            return jsonify({"message": "Forbidden: Insufficient privileges"}), 403
        return wrapper
    return decorator


load_dotenv()
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'super-secret-jwt-key')
print(JWT_SECRET_KEY)

app = Flask(__name__)


print("DATABASE_URL =", os.environ.get("DATABASE_URL"))

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY

db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)


class EndUser(db.Model):
    __tablename__ = 'end_users'
    student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(50), nullable=False, default='voter')  # New field
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

 

class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    manifesto = db.Column(db.Text)
    vote_count = db.Column(db.Integer, default=0)

class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('end_users.student_id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    vote_time = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('student_id', 'election_id', 'position_id', name='unique_vote'), )

class Election(db.Model):
    __tablename__ = 'elections'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Position(db.Model):
    __tablename__ = 'positions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)

class VotingSession(db.Model):
    __tablename__ = 'voting_sessions'
    session_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), nullable=False)


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ("name", "email", "password")):
        return jsonify({"message": "Missing data"}), 400

    if EndUser.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Email already registered"}), 409

    hashed_password = generate_password_hash(data['password'])
    user = EndUser(
        name=data['name'],
        email=data['email'],
        password_hash=hashed_password,
        role='voter'
        
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not all(k in data for k in ("email", "password")):
        return jsonify({"message": "Missing data"}), 400

    user = EndUser.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password_hash, data['password']):
        # Generate JWT token
        access_token = create_access_token(identity=user.student_id, expires_delta=timedelta(hours=1))
        return jsonify({"access_token": access_token, "student_id": user.student_id}), 200
    return jsonify({"message": "Invalid credentials"}), 401



@app.route('/candidates', methods=['GET'])
@jwt_required()
def list_candidates():
    election_id = request.args.get('election_id')
    position_id = request.args.get('position_id')
    query = Candidate.query
    if election_id:
        query = query.filter_by(election_id=election_id)
    if position_id:
        query = query.filter_by(position_id=position_id)
    candidates = query.all()
    output = [{
        "id": c.id,
        "name": c.name,
        "election_id": c.election_id,
        "position_id": c.position_id,
        "manifesto": c.manifesto,
        "vote_count": c.vote_count
    } for c in candidates]
    return jsonify(output), 200

@app.route('/vote', methods=['POST'])
@jwt_required()
def cast_vote():
    data = request.get_json()
    required = ("election_id", "position_id", "candidate_id")
    if not data or not all(k in data for k in required):
        return jsonify({"message": "Missing data"}), 400

    student_id = get_jwt_identity()

    # Check if voting session is open
    now = datetime.utcnow()
    session = VotingSession.query.filter_by(election_id=data['election_id'], status='open').first()
    if not session or not (session.start_time <= now <= session.end_time):
        return jsonify({"message": "Voting is not open for this election"}), 403

    # Prevent double voting
    existing_vote = Vote.query.filter_by(
        student_id=student_id,
        election_id=data['election_id'],
        position_id=data['position_id']
    ).first()
    if existing_vote:
        return jsonify({"message": "You have already voted for this position"}), 400

    vote = Vote(
        student_id=student_id,
        election_id=data['election_id'],
        position_id=data['position_id'],
        candidate_id=data['candidate_id']
    )
    db.session.add(vote)

    candidate = Candidate.query.get(data['candidate_id'])
    if candidate:
        candidate.vote_count += 1

    db.session.commit()
    return jsonify({"message": "Vote cast successfully"}), 201

@app.route('/results', methods=['GET'])
@jwt_required()
def results():
    election_id = request.args.get('election_id')
    position_id = request.args.get('position_id')
    query = Candidate.query
    if election_id:
        query = query.filter_by(election_id=election_id)
    if position_id:
        query = query.filter_by(position_id=position_id)
    candidates = query.order_by(Candidate.vote_count.desc()).all()
    results = [{
        "candidate_id": c.id,
        "name": c.name,
        "election_id": c.election_id,
        "position_id": c.position_id,
        "votes": c.vote_count
    } for c in candidates]
    return jsonify(results), 200


@app.route('/create_election', methods=["POST"])
@jwt_required()
@role_required('admin')
def create_election():
    data = request.get_json()
    required_fields = ["title", "description", "start_time", "end_time"]
    if not data or not all(field in data for field in required_fields):
        return jsonify({"message": "Missing required election data"}), 400

    # Parse datetime fields if necessary
    try:
        start_time = datetime.strptime(data["start_time"], '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(data["end_time"], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return jsonify({"message": "Invalid date format. Use YYYY-MM-DD HH:MM:SS"}), 400

    election = Election(
        title=data["title"],
        description=data["description"],
        start_time=start_time,
        end_time=end_time,
        is_active=True
    )
    db.session.add(election)
    db.session.commit()
    return jsonify({"message": "Election created successfully!", "election_id": election.id}), 201


# Promote User Endpoint
@app.route('/promote_user', methods=["POST"])
@jwt_required()
@role_required('admin')
def promote_user():
    data = request.get_json()
    if not data or not all(k in data for k in ("email", "role")):
        return jsonify({"message": "Missing data"}), 400

    user = EndUser.query.filter_by(email=data['email']).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    user.role = data['role']
    db.session.commit()
    return jsonify({"message": f"{user.email} promoted to {user.role}"}), 200

# Manage Positions Endpoint (Create, Update, Delete)
@app.route('/positions', methods=["POST"])
@jwt_required()
@role_required('admin')
def create_position():
    data = request.get_json()
    if not data or not all(k in data for k in ("election_id", "name")):
        return jsonify({"message": "Missing data"}), 400

    position = Position(
        election_id=data['election_id'],
        name=data['name']
    )
    db.session.add(position)
    db.session.commit()
    return jsonify({"message": "Position created successfully", "position_id": position.id}), 201

@app.route('/positions/<int:position_id>', methods=["PUT"])
@jwt_required()
@role_required('admin')
def update_position(position_id):
    data = request.get_json()
    position = Position.query.get(position_id)
    if not position:
        return jsonify({"message": "Position not found"}), 404

    position.name = data.get('name', position.name)
    db.session.commit()
    return jsonify({"message": "Position updated successfully"}), 200

@app.route('/positions/<int:position_id>', methods=["DELETE"])
@jwt_required()
@role_required('admin')
def delete_position(position_id):
    position = Position.query.get(position_id)
    if not position:
        return jsonify({"message": "Position not found"}), 404

    db.session.delete(position)
    db.session.commit()
    return jsonify({"message": "Position deleted successfully"}), 200

# Start Voting Session Endpoint
@app.route('/start_voting_session', methods=["POST"])
@jwt_required()
@role_required('admin')
def start_voting_session():
    data = request.get_json()
    required = ("election_id", "start_time", "end_time")
    if not data or not all(k in data for k in required):
        return jsonify({"message": "Missing data"}), 400

    # Parse datetime
    try:
        start_time = datetime.strptime(data["start_time"], '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(data["end_time"], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return jsonify({"message": "Invalid date format. Use YYYY-MM-DD HH:MM:SS"}), 400

    # Close existing sessions for this election
    VotingSession.query.filter_by(election_id=data["election_id"], status='open').update({'status': 'closed'})
    session = VotingSession(
        election_id=data["election_id"],
        start_time=start_time,
        end_time=end_time,
        status='open'
    )
    db.session.add(session)
    db.session.commit()
    return jsonify({"message": "Voting session started successfully", "session_id": session.session_id}), 201

# Audit Logs Endpoint (Simple: List all votes and actions)
@app.route('/audit_logs', methods=["GET"])
@jwt_required()
@role_required('admin')
def audit_logs():
    # Simple example: list all votes
    votes = Vote.query.all()
    logs = [{
        "vote_id": v.id,
        "student_id": v.student_id,
        "election_id": v.election_id,
        "position_id": v.position_id,
        "candidate_id": v.candidate_id,
        "vote_time": v.vote_time.strftime('%Y-%m-%d %H:%M:%S')
    } for v in votes]
    return jsonify({"audit_logs": logs}), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({"message": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({"message": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True)