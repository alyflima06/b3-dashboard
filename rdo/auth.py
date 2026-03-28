import bcrypt
from rdo.database import get_setting, update_setting


def verify_coord_password(plain: str) -> bool:
    stored_hash = get_setting("coord_password_hash")
    if not stored_hash:
        return False
    return bcrypt.checkpw(plain.encode(), stored_hash.encode())


def update_coord_password(new_plain: str) -> None:
    new_hash = bcrypt.hashpw(new_plain.encode(), bcrypt.gensalt()).decode()
    update_setting("coord_password_hash", new_hash)
