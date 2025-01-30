"""
Файл с вспомогательными функциями
"""
import io
import re
from PIL import Image
from passlib.context import CryptContext
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def is_valid_username(username):
    return re.fullmatch(r'[A-Za-z0-9]{3,15}', username) is not None

def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def is_image(file_stream):
    try:
        image = Image.open(io.BytesIO(file_stream.read()))
        image.verify()
        file_stream.seek(0)
        return True
    except (IOError, SyntaxError):
        return False

def save_secure_image(file, save_path):
    with Image.open(file) as img:
        img = img.convert('RGB')
        img.thumbnail((500, 500))
        img.save(save_path, 'JPEG')


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)