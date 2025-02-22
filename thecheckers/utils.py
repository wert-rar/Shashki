"""
Файл с вспомогательными функциями
"""
import io
import re
import threading
import itertools
import os
import logging
from PIL import Image
from flask import session, abort
from passlib.context import CryptContext
from werkzeug.utils import secure_filename

ghost_counter = itertools.count(1)
ghost_lock = threading.Lock()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def is_valid_username(username):
    """Проверяет, соответствует ли имя пользователя заданному формату (3-15 символов, буквы и цифры)."""
    return re.fullmatch(r'[A-Za-z0-9]{3,15}', username) is not None

def allowed_file(filename, allowed):
    """Проверяет, имеет ли файл расширение, входящее в список разрешённых."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def is_image(file_stream):
    """Проверяет, является ли переданный файловый поток корректным изображением."""
    try:
        image = Image.open(io.BytesIO(file_stream.read()))
        image.verify()
        file_stream.seek(0)
        return True
    except (IOError, SyntaxError):
        return False

def save_secure_image(file, save_path):
    """Сохраняет изображение в формате JPEG, изменяя его размер до максимальных размеров 500x500 пикселей."""
    with Image.open(file) as img:
        img = img.convert('RGB')
        img.thumbnail((500, 500))
        img.save(save_path, 'JPEG')

def hash_password(password: str) -> str:
    """Возвращает хэш пароля, используя алгоритм bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, соответствует ли открытый пароль его хэшированному значению."""
    return pwd_context.verify(plain_password, hashed_password)

def ensure_user():
    """
        Проверяет наличие пользователя в сессии. Если пользователь отсутствует,
        создаёт ghost-пользователя и сохраняет его в сессии.
    """
    user_login = session.get('user')
    if not user_login:
        with ghost_lock:
            ghost_num = next(ghost_counter)
            ghost_username = f"ghost{ghost_num}"
        session['user'] = ghost_username
        session['is_ghost'] = True
        return ghost_username
    else:
        session['is_ghost'] = user_login.startswith('ghost')
        return user_login

def get_valid_user(session, base):
    """
        Проверяет, что пользователь аутентифицирован и существует в базе данных.
        Если проверка не пройдена, завершает выполнение с ошибкой 403.
        Возвращает логин пользователя и его данные.
    """
    if 'user' not in session:
        logging.warning("Пользователь не аутентифицирован")
        abort(403)
    user_login = session['user']
    user = base.get_user_by_login(user_login)
    if not user or user_login.startswith('ghost'):
        logging.warning("Пользователь не найден или является ghost")
        abort(403)
    return user_login, user

def process_and_save_avatar(file, user_login, upload_folder, allowed_extensions):
    """
        Обрабатывает загруженный файл аватара:
        - Проверяет, выбран ли файл.
        - Проверяет допустимость расширения файла.
        - Проверяет, является ли файл изображением.
        - Сохраняет изображение с безопасным именем.
        Возвращает кортеж (safe_filename, None) при успехе или (None, сообщение об ошибке) при неудаче.
    """
    if file.filename == '':
        return None, "Вы не выбрали файл"
    if not allowed_file(file.filename, allowed_extensions):
        return None, "Недопустимый файл"
    if not is_image(file.stream):
        return None, "Загружаемый файл не является допустимым изображением."
    safe_filename = secure_filename(f"{user_login}.jpg")
    save_path = os.path.join(upload_folder, safe_filename)
    try:
        save_secure_image(file, save_path)
    except Exception:
        logging.exception("Ошибка при сохранении изображения")
        return None, "Ошибка при обработке изображения."
    return safe_filename, None

def remove_old_avatar(old_avatar, current_filename, upload_folder):
    """
        Удаляет старый аватар, если он существует и его имя отличается от текущего.
    """
    if old_avatar and old_avatar != current_filename:
        old_path = os.path.join(upload_folder, old_avatar)
        if os.path.exists(old_path):
            os.remove(old_path)
