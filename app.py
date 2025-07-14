from dotenv import load_dotenv
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta



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
        password_hash=hashed_password
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



@app.errorhandler(404)
def not_found(error):
    return jsonify({"message": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({"message": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True)