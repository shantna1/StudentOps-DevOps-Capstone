import secrets,getpass
from pathlib import Path
from werkzeug.security import generate_password_hash
p=Path('.env')
if p.exists(): raise SystemExit('.env already exists')
p.write_text('MYSQL_ROOT_PASSWORD='+secrets.token_hex(24)+'\nMYSQL_PASSWORD='+secrets.token_hex(24)+'\nSECRET_KEY='+secrets.token_hex(32)+'\nADMIN_PASSWORD_HASH=\''+generate_password_hash(getpass.getpass('Choose admin password: '))+'\'\n')
p.chmod(0o600)
