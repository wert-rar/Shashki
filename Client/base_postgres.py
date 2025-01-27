from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()

DATABASE_URL = "postgresql://postgres:951753aA.@localhost:5432/postgres"
#DATABASE_URL = "postgresql://cloud_user:sqfxuf1Ko&kh@kluysopgednem.beget.app:5432/default_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Game(Base):
    __tablename__ = "games"

    game_id = Column(Integer, primary_key=True, index=True)
    f_user = Column(String, nullable=True)
    c_user = Column(String, nullable=True)
    status = Column(String, default="unstarted")

    moves = relationship("GameMove", back_populates="game")

class GameMove(Base):
    __tablename__ = "game_moves"

    move_id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey('games.game_id'))
    player = Column(String, nullable=False)
    from_x = Column(Integer, nullable=False)
    from_y = Column(Integer, nullable=False)
    to_x = Column(Integer, nullable=False)
    to_y = Column(Integer, nullable=False)
    move_time = Column(DateTime, default=func.now())
    captured_piece = Column(Boolean, default=False)
    promotion = Column(Boolean, default=False)

    game = relationship("Game", back_populates="moves")

class FriendRelation(Base):
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True, index=True)
    user_login = Column(String, nullable=False)
    friend_login = Column(String, nullable=False)
    status = Column(String, default="pending")

class GameInvitation(Base):
    __tablename__ = "game_invitations"

    id = Column(Integer, primary_key=True, index=True)
    from_user = Column(String, nullable=False)
    to_user = Column(String, nullable=False)
    status = Column(String, default="pending")
    game_id = Column(Integer, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)


def send_game_invite_db_with_gameid(sender: str, receiver: str, game_id: int) -> str:
    session = SessionLocal()
    try:
        if sender == receiver:
            return "self_invite"

        existing = session.query(GameInvitation).filter_by(from_user=sender, to_user=receiver, status="pending").first()
        if existing:
            return "already_sent"

        reverse_existing = session.query(GameInvitation).filter_by(from_user=receiver, to_user=sender,
                                                                   status="pending").first()
        if reverse_existing:
            return "reverse_already_sent"

        new_invite = GameInvitation(
            from_user=sender,
            to_user=receiver,
            status="pending",
            game_id=game_id
        )
        session.add(new_invite)
        session.commit()
        return "sent"
    finally:
        session.close()

def send_game_invite_db(sender: str, receiver: str) -> str:
    session = SessionLocal()
    try:
        if sender == receiver:
            return "self_invite"
        existing = session.query(GameInvitation).filter_by(from_user=sender, to_user=receiver, status="pending").first()
        if existing:
            return "already_sent"
        reverse_existing = session.query(GameInvitation).filter_by(from_user=receiver, to_user=sender, status="pending").first()
        if reverse_existing:
            return "reverse_already_sent"
        new_invite = GameInvitation(from_user=sender, to_user=receiver, status="pending")
        session.add(new_invite)
        session.commit()
        return "sent"
    finally:
        session.close()

def get_incoming_game_invites_db(receiver: str) -> list:
    session = SessionLocal()
    try:
        invites = session.query(GameInvitation).filter_by(to_user=receiver, status="pending").all()
        return [{"from_user": i.from_user} for i in invites]
    finally:
        session.close()


def respond_game_invite_db(sender: str, receiver: str, response: str):
    session = SessionLocal()
    try:
        invite = (
            session.query(GameInvitation)
            .filter_by(from_user=sender, to_user=receiver, status="pending")
            .first()
        )
        if not invite:
            return False, None

        if response == "accept":
            invite.status = "accepted"
            session.commit()
            existing_game_id = invite.game_id
            if existing_game_id:
                from game import update_game_with_user_in_db
                try:
                    updated = update_game_with_user_in_db(existing_game_id, receiver, "b")
                    if updated:
                        return True, existing_game_id
                    else:
                        return True, None
                except ValueError:
                    return True, None
            else:
                return True, None
        elif response == "decline":
            invite.status = "declined"
            session.commit()
            return True, None
        else:
            return False, None
    finally:
        session.close()

def send_friend_request_db(sender: str, receiver: str) -> str:
    session = SessionLocal()
    try:
        if sender == receiver:
            return "self_request"

        existing = session.query(FriendRelation).filter_by(user_login=sender, friend_login=receiver).first()
        if existing:
            if existing.status == "pending":
                return "already_sent"
            elif existing.status == "accepted":
                return "already_friends"
            elif existing.status == "declined":
                existing.status = "pending"
                session.commit()
                return "sent_again"
            else:
                return "error"

        reverse_existing = session.query(FriendRelation).filter_by(user_login=receiver, friend_login=sender).first()
        if reverse_existing:
            if reverse_existing.status == "pending":
                return "receiver_already_sent"
            elif reverse_existing.status == "accepted":
                return "already_friends"
            elif reverse_existing.status == "declined":
                reverse_existing.status = "pending"
                session.commit()
                return "sent_again"
            else:
                return "error"

        new_request = FriendRelation(
            user_login=sender,
            friend_login=receiver,
            status="pending"
        )
        session.add(new_request)
        session.commit()
        return "sent"
    finally:
        session.close()

def get_incoming_friend_requests_db(user: str) -> list:
    session = SessionLocal()
    try:
        records = (
            session.query(FriendRelation)
            .filter_by(friend_login=user, status="pending")
            .all()
        )
        return [r.user_login for r in records]
    finally:
        session.close()

def respond_friend_request_db(sender: str, receiver: str, response: str) -> bool:
    session = SessionLocal()
    try:
        record = (
            session.query(FriendRelation)
            .filter_by(user_login=sender, friend_login=receiver, status="pending")
            .first()
        )
        if not record:
            return False

        if response == "accept":
            record.status = "accepted"
        elif response == "decline":
            record.status = "declined"
        else:
            return False

        session.commit()
        return True
    finally:
        session.close()

def get_friends_db(user: str) -> list:
    session = SessionLocal()
    try:
        sent_accepted = (
            session.query(FriendRelation)
            .filter_by(user_login=user, status="accepted")
            .all()
        )
        received_accepted = (
            session.query(FriendRelation)
            .filter_by(friend_login=user, status="accepted")
            .all()
        )
        friends = [rel.friend_login for rel in sent_accepted] + [rel.user_login for rel in received_accepted]
        return list(set(friends))
    finally:
        session.close()

def remove_friend_db(user: str, friend_username: str) -> bool:
    session = SessionLocal()
    try:
        relations = session.query(FriendRelation).filter(
            ((FriendRelation.user_login == user) & (FriendRelation.friend_login == friend_username)) |
            ((FriendRelation.user_login == friend_username) & (FriendRelation.friend_login == user))
        ).all()

        if not relations:
            return False
        for rel in relations:
            session.delete(rel)
        session.commit()
        return True
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
