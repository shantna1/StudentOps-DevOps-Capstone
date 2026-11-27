import os
os.environ['SECRET_KEY']='test-only'
os.environ['DATABASE_URL']='sqlite:///:memory:'
from app import app,db

def test_crud():
    app.config.update(TESTING=True,WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
        c=app.test_client()
        assert c.get('/health').status_code==200
        assert c.get('/api/students').status_code==401
        with c.session_transaction() as s: s['admin']=True
        data=dict(roll='1',name='Demo',email='demo@example.com',course='CSE',semester=7)
        r=c.post('/api/students',json=data); assert r.status_code==201
        i=r.json['id']; assert c.get(f'/api/students/{i}').json['name']=='Demo'
        data['name']='Updated'; assert c.put(f'/api/students/{i}',json=data).status_code==200
        assert c.delete(f'/api/students/{i}').status_code==204
        db.drop_all()
