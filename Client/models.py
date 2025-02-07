from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from sqlalchemy.orm import declarative_base

Base = declarative_base()


#--------------------------------------------------------Tables from sqlite---------------------------------------------
class Player(Base):
    __tablename__ = 'players'
    user_id = Column(BigInteger, primary_key=True, index=True)
    login = Column(String, unique=True)
    password = Column(String)
    rang = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    avatar_filename = Column(String)

    def __iter__(self):
        """
        Позволяет преобразовать объект Player в словарь с помощью dict().
        """
        yield from {
            "user_id": self.user_id,
            "login": self.login,
            "password": self.password,
            "rang": self.rang,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "avatar_filename": self.avatar_filename
        }.items()

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "login": self.login,
            "rang": self.rang,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "avatar_filename": self.avatar_filename
        }


class CompletedGames(Base):
    __tablename__ = 'completed_games'
    ID = Column(Integer, primary_key=True, index=True)
    user_login = Column(String, nullable=False)
    game_id = Column(BigInteger)
    date_start = Column(String, nullable=False)
    rating_before = Column(Integer)
    rating_after = Column(Integer)
    rating_change = Column(Integer)
    result = Column(String)

    def to_dict(self):
        return {
            "ID": self.ID,
            "user_login": self.user_login,
            "game_id": self.game_id,
            "date_start": self.date_start,
            "rating_before": self.rating_before,
            "rating_after": self.rating_after,
            "rating_change": self.rating_change,
            "result": self.result
        }


class RememberToken(Base):
    __tablename__ = 'remember_token'
    ID = Column(Integer, primary_key=True, index=True)
    user_login = Column(String)
    token = Column(String, unique=True)
    expires_at = Column(String)


# ----------------------------------------------------------------------------------------------------------------------

class Game(Base):
    __tablename__ = "games"
    game_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    f_user = Column(String, nullable=True)
    c_user = Column(String, nullable=True)
    status = Column(String, default="unstarted")
    board_state = Column(String, nullable=True)
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

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, unique=True)
    game_id = Column(Integer, ForeignKey('games.game_id'), nullable=True)
    room_creator = Column(String, nullable=False)
    occupant = Column(String, nullable=True)
    chosen_white = Column(String, nullable=True)
    chosen_black = Column(String, nullable=True)
