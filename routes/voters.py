from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from models import Election, Position
from datetime import datetime

voter_bp = Blueprint('voter', __name__)

@voter_bp.route('/positions', methods=['GET'])
@jwt_required()
def get_positions():
    now = datetime.utcnow()
    active_election = Election.query.filter(Election.start_time <= now, Election.end_time >= now).first()
    if not active_election:
        return jsonify([]), 200

    positions = Position.query.filter_by(election_id=active_election.id).all()
    return jsonify([{
        "id": p.id,
        "name": p.name,
        "election_id": p.election_id
    } for p in positions]), 200