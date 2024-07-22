import bcrypt

def hash_password(password):
    # Generate a salt
    salt = bcrypt.gensalt()
    # Hash the password
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed

def check_password(password, hashed):
    # Check the password
    return bcrypt.checkpw(password.encode(), hashed)