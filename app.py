from dotenv import load_dotenv
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta,timezone
from functools import wraps
from flask_cors import CORS
from models import db
from models import Candidate,EndUser,VotingSession,Voter,Vote
from zoneinfo import ZoneInfo








load_dotenv()
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'super-secret-jwt-key')

app = Flask(__name__)

CORS(app, origins=["http://localhost:5173"], supports_credentials=True)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY

db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)


# Role check decorator
def role_required(required_role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = int(get_jwt_identity())
            user = EndUser.query.get(user_id)
            if user and user.role == required_role:
                return fn(*args, **kwargs)
            return jsonify({"message": "Forbidden: Insufficient privileges"}), 403
        return wrapper
    return decorator

# Register blueprint after db is initialized
from routes.admin import admin_bp
app.register_blueprint(admin_bp)

from routes.voters import voter_bp
app.register_blueprint(voter_bp)

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
        access_token = create_access_token(identity=str(user.student_id), expires_delta=timedelta(hours=1))
        return jsonify({"access_token": access_token, "student_id": user.student_id, "role": user.role}), 200
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
    output = [c.to_dict() for c in candidates]
    return jsonify(output), 200




from datetime import datetime
from zoneinfo import ZoneInfo  # Requires Python 3.9+
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import VotingSession, Vote, Candidate, db

@app.route('/vote', methods=['POST'])
@jwt_required()
def cast_vote():
    data = request.get_json()
    required = ("election_id", "position_id", "candidate_id")
    if not data or not all(k in data for k in required):
        return jsonify({"message": "Missing data"}), 400

    student_id = get_jwt_identity()
    
    
    nairobi = ZoneInfo("Africa/Nairobi")
    now = datetime.now(nairobi)

    session = VotingSession.query.filter_by(
        election_id=data['election_id']
    ).first()

    if not session:
        return jsonify({"message": "No session found for this election"}), 403

    # Convert session times to Nairobi timezone
    if session.start_time.tzinfo is None:
        session.start_time = session.start_time.replace(tzinfo=ZoneInfo("Africa/Nairobi"))
    if session.end_time.tzinfo is None:
        session.end_time = session.end_time.replace(tzinfo=ZoneInfo("Africa/Nairobi"))

    print("Now:", now)
    print("Session start:", session.start_time)
    print("Session end:", session.end_time)
    print("Session status before update:", session.status)

    if session.status == 'scheduled' and session.start_time <= now <= session.end_time:
        session.status = 'open'
        db.session.commit()

    if session.status != 'open' or not (session.start_time <= now <= session.end_time):
        return jsonify({"message": "Voting is not open for this election"}), 403

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
        candidate.votes += 1

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
@app.route('/admin/login', methods=['POST', 'OPTIONS'])
def admin_login():
    if request.method == 'OPTIONS':
        # Handle CORS preflight
        return jsonify({}), 200
    data = request.get_json()
    if not data or not all(k in data for k in ("email", "password")):
        return jsonify({"message": "Missing data"}), 400

    user = EndUser.query.filter_by(email=data['email'], role='admin').first()
    if user and check_password_hash(user.password_hash, data['password']):
        access_token = create_access_token(identity=str(user.student_id), expires_delta=timedelta(hours=1))
        return jsonify({"access_token": access_token, "student_id": user.student_id, "role": user.role}), 200
    return jsonify({"message": "Invalid credentials or not an admin"}), 401

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

@app.errorhandler(404)
def not_found(error):
    return jsonify({"message": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({"message": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True)