from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Election(db.Model):
    __tablename__ = 'elections' 
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="upcoming")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    candidates = db.relationship('Candidate', backref='election', lazy=True)
    positions = db.relationship('Position', backref='election', lazy=True)

    @property
    def is_active(self):
        now = datetime.utcnow()
        return self.start_time <= now <= self.end_time and self.status == "active"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
        }

class Position(db.Model):
    __tablename__ = 'positions'  
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False) 

    candidates = db.relationship('Candidate', backref='position', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "election_id": self.election_id,
        }

class Candidate(db.Model):
    __tablename__ = 'candidates'  
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False) 
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)  
    votes = db.Column(db.Integer, default=0)
    

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "election_id": self.election_id,
            "position_id": self.position_id,
            "votes": self.votes,
        }

class Voter(db.Model):
    __tablename__ = 'voters' 
    student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False, default='voter')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "student_id": self.student_id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class EndUser(db.Model):
    __tablename__ = 'end_users'
    student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(50), nullable=False, default='voter')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "student_id": self.student_id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('end_users.student_id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)  
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)  
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False) 
    vote_time = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'election_id', 'position_id', name='unique_vote'),
    )

class VotingSession(db.Model):
    __tablename__ = 'voting_sessions'
    session_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False) 
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), nullable=False)
