from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Election, Candidate, Voter, Position,EndUser,VotingSession
from app import role_required
from datetime import datetime
from zoneinfo import ZoneInfo

    

admin_bp = Blueprint('admin', __name__)

def _election_to_dict(e):
    now = datetime.utcnow()
    if now < e.start_time:
        status = "inactive"
    elif now < e.start_time:
        status = "upcoming"
    elif e.start_time <= now <= e.end_time:
        status = "active"
    else:   
        status = "completed"
    return {
        "id": e.id,
        "title": e.title,
        "description": e.description,
        "start_time": e.start_time.strftime('%Y-%m-%d %H:%M:%S'),
        "end_time": e.end_time.strftime('%Y-%m-%d %H:%M:%S'),
        "status": status,
        "created_at": e.created_at.strftime('%Y-%m-%d %H:%M:%S') if e.created_at else None

    }

def _candidate_to_dict(c):
    return {
        "id": c.id,
        "name": c.name,
        "election_id": c.election_id,
        "position_id": c.position_id,
        "vote_count": c.votes
    }

def _position_to_dict(p):
    return {
        "id": p.id,
        "name": p.name,
        "election_id": p.election_id
    }

def _voter_to_dict(v):
    return {
        "student_id": v.student_id,
        "name": v.name,
        "email": v.email,
        "role": v.role,
        "created_at": v.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }

@admin_bp.route('/admin/elections', methods=['GET'])
@jwt_required()
@role_required('admin')
def list_elections():
    elections = Election.query.order_by(Election.start_time.desc()).all()
    return jsonify({"elections": [_election_to_dict(e) for e in elections]}), 200

@admin_bp.route('/admin/elections/<int:election_id>', methods=['GET'])
@jwt_required()
@role_required('admin')
def election_details(election_id):
    election = Election.query.get_or_404(election_id)
    positions = Position.query.filter_by(election_id=election_id).all()
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    return jsonify({
        "election": _election_to_dict(election),
        "positions": [_position_to_dict(p) for p in positions],
        "candidates": [_candidate_to_dict(c) for c in candidates]
    }), 200

@admin_bp.route('/admin/elections', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_election():
    data = request.get_json()
    required_fields = ["title", "description", "start_time", "end_time"]

    if not data or not all(field in data and data[field].strip() for field in required_fields):
        return jsonify({"message": "Missing required election data"}), 400

    try:
        start_time = datetime.strptime(data["start_time"], '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(data["end_time"], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return jsonify({"message": "Invalid date format. Use YYYY-MM-DD HH:MM:SS"}), 400

    if end_time <= start_time:
        return jsonify({"message": "End time must be after start time."}), 400

    election = Election(
        title=data["title"],
        description=data["description"],
        start_time=start_time,
        end_time=end_time,
        status="upcoming"
    )

    db.session.add(election)
    db.session.commit() 

    
    session = VotingSession(
        election_id=election.id,
        start_time=start_time,
        end_time=end_time,
        status="open" if start_time <= datetime.utcnow() <= end_time else "scheduled"
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        "msg": "Election and session created",
        "election": {
            "id": election.id,
            "title": election.title,
            "description": election.description,
            "start_time": election.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "end_time": election.end_time.strftime('%Y-%m-%d %H:%M:%S'),
            "status": election.status
        },
        "session": {
            "id": session.session_id,
            "start_time": session.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "end_time": session.end_time.strftime('%Y-%m-%d %H:%M:%S'),
            "status": session.status
        }
    }), 201


@admin_bp.route('/admin/elections/<int:election_id>', methods=['PUT'])
@jwt_required()
@role_required('admin')
def edit_election(election_id):
    election = Election.query.get_or_404(election_id)
    data = request.get_json()
    if "title" in data:
        election.title = data["title"]
    if "description" in data:
        election.description = data["description"]
    if "start_time" in data:
        try:
            election.start_time = datetime.strptime(data["start_time"], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"message": "Invalid date format. Use YYYY-MM-DD HH:MM:SS"}), 400
    if "end_time" in data:
        try:
            election.end_time = datetime.strptime(data["end_time"], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"message": "Invalid date format. Use YYYY-MM-DD HH:MM:SS"}), 400
    db.session.commit()
    return jsonify({"msg": "Election updated", "election": _election_to_dict(election)}), 200

@admin_bp.route('/admin/elections/<int:election_id>', methods=['DELETE'])
@jwt_required()
@role_required('admin')
def delete_election(election_id):
    election = Election.query.get_or_404(election_id)
    db.session.delete(election)
    db.session.commit()
    return jsonify({"msg": "Election deleted"}), 200

@admin_bp.route('/admin/voters', methods=['GET'])
@jwt_required()
@role_required('admin')
def list_voters():
    voters = EndUser.query.all()
    return jsonify({"voters": [_voter_to_dict(v) for v in voters]}), 200

@admin_bp.route('/admin/elections/<int:election_id>/positions', methods=['POST'])
@jwt_required()
@role_required('admin')
def add_position(election_id):
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"message": "Missing position name"}), 400
    position = Position(name=data['name'], election_id=election_id)
    db.session.add(position)
    db.session.commit()
    return jsonify({"msg": "Position added", "position": _position_to_dict(position)}), 201

@admin_bp.route('/admin/elections/<int:election_id>/candidates', methods=['POST'])
@jwt_required()
@role_required('admin')
def add_candidate(election_id):
    data = request.get_json()
    if not data or not all(k in data for k in ["name", "position_id"]):
        return jsonify({"message": "Missing candidate data"}), 400
    candidate = Candidate(
        name=data['name'],
        election_id=election_id,
        position_id=data['position_id']
    )
    db.session.add(candidate)
    db.session.commit()
    return jsonify({"msg": "Candidate added", "candidate": _candidate_to_dict(candidate)}), 201

@admin_bp.route('/admin/elections/<int:election_id>/results', methods=['GET'])
@jwt_required()
@role_required('admin')
def election_results(election_id):
    positions = Position.query.filter_by(election_id=election_id).all()
    results = []
    for pos in positions:
        candidates = Candidate.query.filter_by(position_id=pos.id).all()
        results.append({
            "position": pos.name,
            "candidates": [
                {"name": c.name, "votes": c.votes} for c in candidates
            ]
        })
    return jsonify({"results": results}), 200

@admin_bp.route('/admin/candidates/<int:candidate_id>', methods=['GET'])
@jwt_required()
def candidate_profile(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    return jsonify(_candidate_to_dict(candidate)), 200

@admin_bp.route('/admin/elections/upcoming', methods=['GET'])
@jwt_required()
def upcoming_elections():
    now = datetime.utcnow()
    elections = Election.query.filter(Election.start_time > now).order_by(Election.start_time.asc()).all()
    return jsonify({"elections": [_election_to_dict(e) for e in elections]}), 200

@admin_bp.route('/admin/elections/active', methods=['GET'])
@jwt_required()
def active_elections():
    now = datetime.utcnow()
    elections = Election.query.filter(Election.start_time <= now, Election.end_time >= now).order_by(Election.start_time.asc()).all()
    return jsonify({"elections": [_election_to_dict(e) for e in elections]}), 200



@admin_bp.route('/admin/sessions', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_voting_session():
    data = request.get_json()
    required_fields = ['election_id', 'start_time', 'end_time']

    if not data or not all(field in data for field in required_fields):
        return jsonify({"message": "Missing required session data"}), 400

    try:
        # Parse input and apply Nairobi timezone
        nairobi = ZoneInfo("Africa/Nairobi")
        start_time = datetime.strptime(data['start_time'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=nairobi)
        end_time = datetime.strptime(data['end_time'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=nairobi)

        if end_time <= start_time:
            return jsonify({"message": "End time must be after start time"}), 400

        # Auto-determine session status if not provided or invalid
        now = datetime.now(nairobi)
        status = data.get('status', '').lower()
        if status not in ['open', 'scheduled', 'closed']:
            status = 'open' if start_time <= now <= end_time else 'scheduled'

    except Exception as e:
        return jsonify({"message": f"Invalid input: {str(e)}"}), 400

    session = VotingSession(
        election_id=data['election_id'],
        start_time=start_time,
        end_time=end_time,
        status=status
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        "message": "Voting session created successfully",
        "session": {
            "id": session.session_id,
            "election_id": session.election_id,
            "start_time": session.start_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
            "end_time": session.end_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
            "status": session.status
        }
    }), 201
