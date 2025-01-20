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


def init_db():
    Base.metadata.create_all(bind=engine)


def send_friend_request_db(sender: str, receiver: str) -> bool:
    session = SessionLocal()
    try:
        existing = session.query(FriendRelation).filter_by(user_login=sender, friend_login=receiver).first()
        if existing:
            if existing.status in ("pending", "accepted"):
                return True
            else:
                existing.status = "pending"
                session.commit()
                return True
        else:
            reverse_existing = (
                session.query(FriendRelation)
                .filter_by(user_login=receiver, friend_login=sender)
                .first()
            )
            if reverse_existing and reverse_existing.status == "accepted":
                return False

            new_request = FriendRelation(
                user_login=sender,
                friend_login=receiver,
                status="pending"
            )
            session.add(new_request)
            session.commit()
            return True
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
