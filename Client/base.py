from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, select, update, and_, or_
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import logging

import utils
from Client.models import Player, CompletedGames, RememberToken, FriendRelation, GameInvitation, GameMove

Base = declarative_base()

DATABASE_URL = "postgresql://postgres:951753aA.@localhost:5432/postgres"
#DATABASE_URL = "postgresql://cloud_user:sqfxuf1Ko&kh@kluysopgednem.beget.app:5432/default_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



def connect(method):
    """
            A decorator function that establishes a connection to the database and manages the session.
            It wraps the provided method and ensures that the database session is properly initialized, committed, and closed.

            Parameters:
            method (callable): The function to be decorated. This function should accept a database session as a keyword argument.

            Returns:
            wrapper (callable): The decorated function. This function will handle the database session management.
        """

    def wrapper(*args, **kwargs):
        with SessionLocal() as session:
            try:
                return  method(*args, session=session)
            except Exception as e:
                session.rollback()
                raise Exception(f'Ошибка при работе с базой данных: {repr(e)} args:\n{args} kwargs:\n{kwargs}')
            finally:
                session.close()

    return wrapper



def init_db():
    Base.metadata.create_all(bind=engine)

# ----------------------------------------------------------------------------------------------------------------------

@connect
def check_user_exists(user_login, session: Session | None = None):
    return session.scalar(select(Player).where(Player.login == user_login)) is not None


@connect
def register_user(user_login, user_password,session: Session | None = None):
    if check_user_exists(user_login):
        logging.warning(f"Пользователь с логином '{user_login}' уже существует.")
        return False

    hashed_password = utils.hash_password(user_password)

    try:
        session.add(Player(login=user_login, password=hashed_password))
        session.commit()
        return True
    except Exception as e:
        logging.error(f"Ошибка при регистрации пользователя: {e}")
        return False

@connect
def authenticate_user(user_login, user_password,session: Session | None = None):

    row = session.scalar(select(Player).where(Player.login == user_login))
    if row:
        stored_password = row["password"]
        if utils.verify_password(user_password, stored_password):
            logging.info(f"Пользователь '{user_login}' успешно аутентифицирован.")
            return True
        else:
            logging.warning(f"Неверный пароль для пользователя '{user_login}'.")
            return False
    else:
        logging.warning(f"Пользователь '{user_login}' не найден.")
        return False

@connect
def get_user_by_login(user_login,session: Session | None = None) -> Player:
    return session.scalar(select(Player).where(Player.login == user_login))


@connect
def update_user_rang(user_login, points, session: Session | None = None):

    session.execute(update(Player).where(Player.login == user_login).values(rang=Player.rang + points))
    session.commit()

@connect
def update_user_stats(user_login, wins=0, losses=0, draws=0, session: Session | None = None):
    session.execute(update(Player).where(Player.login == user_login).values(wins=Player.wins + wins, losses=Player.losses + losses, draws=Player.draws + draws))
    session.commit()

@connect
def add_completed_game(user_login, game_id, date_start, rating_before, rating_after, rating_change, result,session: Session | None = None):

    session.add(CompletedGames(user_login=user_login, game_id=game_id, date_start=date_start,
                               rating_before=rating_before, rating_after=rating_after, rating_change = rating_change,
                               result=result))
    session.commit()

@connect
def get_user_history(user_login,session: Session | None = None):

    result = session.execute(select(CompletedGames).where(CompletedGames.user_login == user_login).order_by(CompletedGames.ID.asc()))
    return [dict(game_history) for  game_history in result]

@connect
def update_user_avatar(user_login, filename, session: Session | None = None):
    session.execute(update(Player).where(Player.login == user_login).values(avatar_filename=filename))
    session.commit()


@connect
def add_remember_token(user_login, token, expires_at, session: Session | None = None):
    try:
        session.add(RememberToken(user_login=user_login, token=token, expires_at=expires_at.isoformat()))
        logging.info(f"Токен для пользователя '{user_login}' добавлен.")
        return True
    except Exception as e:
        logging.error(f"Ошибка при добавлении токена: {e}")
        return False

@connect
def get_user_by_remember_token(token,session: Session | None = None):

    row = session.scalar(select(RememberToken).where(RememberToken.token == token))
    if row:
        expires_at = datetime.fromisoformat(row.expires_at)
        if datetime.now() < expires_at:
            return row.user_login
        else:
            delete_remember_token(token,session)
            return None
    return None

@connect
def delete_remember_token(token, session: Session | None = None):
    try:
        r = session.scalar(select(RememberToken).where(RememberToken.token==token))
        session.delete(r)
        session.commit()
        logging.info(f"Токен '{token}' удален.")
    except Exception as e:
        logging.error(f"Ошибка при удалении токена: {e}")

@connect
def delete_all_remember_tokens(user_login, session: Session | None = None):
    try:
        r = session.scalars(select(RememberToken).where(RememberToken.user_login== user_login))
        session.delete(r)
        session.commit()
        logging.info(f"Все токены для пользователя '{user_login}' удалены.")
    except Exception as e:
        logging.error(f"Ошибка при удалении токенов: {e}")

@connect
def search_users(query: str, exclude_user: str = None, limit: int = 10, session: Session | None = None):
    if not query:
        return []

    try:

        like_query = f"{query}%"
        if exclude_user:
            stmt = select(Player.login).where(
                and_(
                    Player.login.like(like_query),
                    Player.login != exclude_user
                )
            ).limit(limit)
        else:
            stmt = select(Player.login).where(
                Player.login.like(like_query)
            ).limit(limit)
        rows = session.scalars(stmt)
        return [row.user_login for row in rows]
    except Exception as e:
        logging.error(f"Ошибка при поиске пользователей: {e}")
        return []

@connect
def get_top_players(limit: int = 3,  session: Session | None = None):
    try:
        stmt = select(Player).order_by(Player.rang.desc()).limit(limit)

        # Выполняем запрос
        result = session.execute(stmt)
        rows = result.scalars().all()

        # Преобразуем результаты в список словарей
        top_players = []
        for row in rows:
            top_players.append({
                "login": row.login,
                "rang": row.rang,
                "avatar_filename": row.avatar_filename
            })

        return top_players
    except Exception as e:
        logging.error(f"Ошибка при получении топ игроков: {e}")
        return []


# ----------------------------------------------------------------------------------------------------------------------


@connect
def send_game_invite_db(sender: str, receiver: str, session: Session | None = None) -> str:

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

@connect
def send_friend_request_db(sender: str, receiver: str, session: Session | None = None) -> str:
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

@connect
def get_incoming_friend_requests_db(user: str, session: Session | None = None) -> list:
        records = (
            session.query(FriendRelation)
            .filter_by(friend_login=user, status="pending")
            .all()
        )
        return [r.user_login for r in records]

@connect
def respond_friend_request_db(sender: str, receiver: str, response: str, session: Session | None = None) -> bool:
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

@connect
def get_friends_db(user: str, session: Session | None = None) -> list:
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

@connect
def remove_friend_db(user: str, friend_username: str, session: Session | None = None) -> bool:
        relations = session.query(FriendRelation).filter(
            or_(and_((FriendRelation.user_login == user),(FriendRelation.friend_login == friend_username)),
            and_((FriendRelation.user_login == friend_username),(FriendRelation.friend_login == user)))
        ).all()

        if not relations:
            return False
        for rel in relations:
            session.delete(rel)
        session.commit()
        return True

@connect
def add_move(game_id:int, move_record:dict, session: Session | None = None):

    session.add(GameMove(
        game_id=game_id,
        player=move_record['player'],
        from_x=move_record['from']['x'],
        from_y=move_record['from']['y'],
        to_x=move_record['to']['x'],
        to_y=move_record['to']['y'],
        captured_piece=move_record['captured'],
        promotion=move_record['promotion']
    ))
    session.commit()
    session.close()

@connect
def get_game_moves_from_db(game_id, session: Session | None = None):
    moves = session.query(GameMove).filter_by(game_id=game_id).order_by(GameMove.move_id).all()
    move_list = []
    for m in moves:
        move_list.append({
            "player": m.player,
            "from": {"x": m.from_x, "y": m.from_y},
            "to": {"x": m.to_x, "y": m.to_y},
            "captured": m.captured_piece,
            "promotion": m.promotion
        })
    return move_list




if __name__ == "__main__":
    init_db()
