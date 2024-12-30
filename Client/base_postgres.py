from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import json

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

class GamePieces(Base):
    __tablename__ = "games_pieces"
    game_id = Column(Integer, primary_key=True, index=True)
    pieces = Column(String, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_pieces_by_game_id(db_session, game_id):
    row = db_session.query(GamePieces).filter(GamePieces.game_id == game_id).first()
    if not row:
        return None
    return json.loads(row.pieces)

def create_or_update_pieces(db_session, game_id, pieces):
    row = db_session.query(GamePieces).filter(GamePieces.game_id == game_id).first()
    if not row:
        row = GamePieces(game_id=game_id, pieces=json.dumps(pieces))
        db_session.add(row)
    else:
        row.pieces = json.dumps(pieces)
    db_session.commit()

if __name__ == "__main__":
    init_db()