import subprocess
from pathlib import Path
v=dict(line.split('=',1) for line in Path('.env').read_text().splitlines()); v={k:x.strip("'") for k,x in v.items()}; v['DATABASE_URL']='mysql+pymysql://student:'+v['MYSQL_PASSWORD']+'@db/students'
import json
subprocess.run(['kubectl','apply','-f','-'],input=json.dumps({'apiVersion':'v1','kind':'Secret','metadata':{'name':'studentops-secret','namespace':'studentops'},'stringData':v}),text=True,check=True)
