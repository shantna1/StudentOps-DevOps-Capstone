import os, logging
from datetime import date
from sqlalchemy import func
from functools import wraps
from flask import Flask, request, session, redirect, url_for, render_template, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from prometheus_flask_exporter import PrometheusMetrics
from flask_wtf.csrf import CSRFProtect
app=Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY'), SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL','sqlite:///students.db'), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
if not app.secret_key: raise RuntimeError('Set SECRET_KEY')
db=SQLAlchemy(app); CSRFProtect(app); PrometheusMetrics(app)
logging.basicConfig(level=logging.INFO)
class Student(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    roll=db.Column(db.String(40),unique=True,nullable=False)
    name=db.Column(db.String(100),nullable=False)
    email=db.Column(db.String(120),nullable=False)
    course=db.Column(db.String(100),nullable=False)
    semester=db.Column(db.Integer,nullable=False)
    def data(self): return {k:getattr(self,k) for k in ('id','roll','name','email','course','semester')}
class Fee(db.Model):
    student_id=db.Column(db.Integer,db.ForeignKey('student.id',ondelete='CASCADE'),primary_key=True)
    total=db.Column(db.Integer,nullable=False,default=0)
    paid=db.Column(db.Integer,nullable=False,default=0)
class Attendance(db.Model):
    student_id=db.Column(db.Integer,db.ForeignKey('student.id',ondelete='CASCADE'),primary_key=True)
    day=db.Column(db.Date,primary_key=True)
    status=db.Column(db.String(10),nullable=False)
class Timetable(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    day=db.Column(db.Integer,nullable=False)
    start=db.Column(db.String(5),nullable=False)
    end=db.Column(db.String(5),nullable=False)
    subject=db.Column(db.String(100),nullable=False)
    room=db.Column(db.String(40),nullable=False)
    course=db.Column(db.String(100),nullable=False)
    semester=db.Column(db.Integer,nullable=False)
Student.fee=db.relationship(Fee,cascade='all, delete-orphan',uselist=False)
Student.attendance=db.relationship(Attendance,cascade='all, delete-orphan')
def auth(f):
    @wraps(f)
    def wrapped(*a,**kw):
        if not session.get('admin'): return (jsonify(error='Unauthorized'),401) if request.path.startswith('/api/') else redirect(url_for('login'))
        return f(*a,**kw)
    return wrapped
@app.route('/login',methods=['GET','POST'])
def login():
    error=None
    if request.method=='POST':
        if request.form.get('username')==os.getenv('ADMIN_USER','admin') and check_password_hash(os.getenv('ADMIN_PASSWORD_HASH','invalid'),request.form.get('password','')):
            session.clear(); session['admin']=True; return redirect('/')
        error='Invalid credentials'
    return render_template('login.html',error=error)
@app.post('/logout')
def logout(): session.clear(); return redirect('/login')
@app.get('/health')
def health():
    from sqlalchemy import text
    db.session.execute(text('SELECT 1')); return {'status':'healthy'}
@app.get('/')
@auth
def home():
    q=request.args.get('q',''); students=Student.query.filter(Student.name.contains(q)|Student.roll.contains(q)).order_by(Student.id.desc()).all()
    return render_template('index.html',students=students,total=Student.query.count(),q=q, collected=db.session.query(func.coalesce(func.sum(Fee.paid),0)).scalar(), pending=db.session.query(func.coalesce(func.sum(Fee.total-Fee.paid),0)).scalar(), present=Attendance.query.filter_by(status="Present").count(), marked=Attendance.query.count())
def save(s,data):
    for k in ('roll','name','email','course'):
        v=str(data.get(k,'')).strip()
        if not v or len(v)>({'roll':40,'name':100,'email':120,'course':100}[k]): abort(400,description='Invalid '+k)
        setattr(s,k,v)
    try: s.semester=int(data.get('semester',0))
    except (ValueError,TypeError): abort(400,description='Invalid semester')
    if not 1<=s.semester<=8 or '@' not in s.email: abort(400,description='Invalid email or semester')
    db.session.add(s)
    from sqlalchemy.exc import IntegrityError
    try: db.session.commit()
    except IntegrityError: db.session.rollback(); abort(409,description='Duplicate roll number')
    app.logger.info('Student saved id=%s',s.id)
@app.route('/student/new',methods=['GET','POST'])
@app.route('/student/<int:id>/edit',methods=['GET','POST'])
@auth
def edit(id=None):
    s=db.get_or_404(Student,id) if id else Student()
    if request.method=='POST': save(s,request.form); return redirect('/')
    return render_template('edit.html',s=s)
@app.post('/student/<int:id>/delete')
@auth
def delete(id):
    db.session.delete(db.get_or_404(Student,id)); db.session.commit(); return redirect('/')
@app.route('/api/students',methods=['GET','POST'])
@auth
def api():
    if request.method=='POST':
        s=Student(); save(s,request.get_json()); return jsonify(s.data()),201
    return jsonify([s.data() for s in Student.query.all()])
@app.route('/api/students/<int:id>',methods=['GET','PUT','DELETE'])
@auth
def api_one(id):
    s=db.get_or_404(Student,id)
    if request.method=='DELETE': db.session.delete(s); db.session.commit(); return '',204
    if request.method=='PUT': save(s,request.get_json())
    return jsonify(s.data())
@app.route('/fees',methods=['GET','POST'])
@auth
def fees():
    if request.method=='POST':
        student=db.get_or_404(Student,request.form.get('student_id',type=int))
        total=request.form.get('total',type=int); paid=request.form.get('paid',type=int)
        if total is None or paid is None or not 0<=paid<=total<=10000000: abort(400,description='Invalid fee amounts')
        f=db.session.get(Fee,student.id) or Fee(student_id=student.id)
        f.total=total; f.paid=paid; db.session.add(f); db.session.commit(); return redirect('/fees')
    return render_template('fees.html',students=Student.query.order_by(Student.roll).all())
@app.route('/attendance',methods=['GET','POST'])
@auth
def attendance():
    try: day=date.fromisoformat(request.values.get('day',date.today().isoformat()))
    except ValueError: abort(400,description='Invalid date')
    students=Student.query.order_by(Student.roll).all()
    if request.method=='POST':
        for student in students:
            status=request.form.get(f'status_{student.id}')
            if status not in ('Present','Absent','Leave',''): abort(400,description='Invalid status')
            a=db.session.get(Attendance,(student.id,day))
            if not status:
                if a: db.session.delete(a)
            else:
                a=a or Attendance(student_id=student.id,day=day); a.status=status; db.session.add(a)
        db.session.commit(); return redirect(url_for('attendance',day=day.isoformat()))
    records={a.student_id:a.status for a in Attendance.query.filter_by(day=day).all()}
    return render_template('attendance.html',students=students,records=records,day=day.isoformat())
@app.route('/timetable',methods=['GET','POST'])
@auth
def timetable():
    if request.method=='POST':
        from datetime import time
        d=request.form.get('day',type=int); sem=request.form.get('semester',type=int)
        start=request.form.get('start',''); end=request.form.get('end','')
        try: valid=time.fromisoformat(start)<time.fromisoformat(end)
        except ValueError: valid=False
        fields={k:request.form.get(k,'').strip() for k in ('subject','room','course')}
        if d not in range(5) or sem not in range(1,9) or not valid or len(start)!=5 or len(end)!=5 or any(not v or len(v)>(40 if k=='room' else 100) for k,v in fields.items()): abort(400,description='Invalid class details')
        db.session.add(Timetable(day=d,semester=sem,start=start,end=end,**fields)); db.session.commit(); return redirect('/timetable')
    return render_template('timetable.html',classes=Timetable.query.order_by(Timetable.day,Timetable.start).all(),days=['Monday','Tuesday','Wednesday','Thursday','Friday'])
@app.post('/timetable/<int:id>/delete')
@auth
def remove_class(id):
    db.session.delete(db.get_or_404(Timetable,id)); db.session.commit(); return redirect('/timetable')
@app.cli.command('seed-demo')
def seed_demo():
    db.create_all()
    names=['Aarav Sharma','Ananya Gupta','Rohan Verma','Priya Singh','Aditya Kumar','Ishita Patel','Arjun Mehta','Sneha Yadav','Vivaan Joshi','Kavya Rao','Rahul Mishra','Diya Das','Karan Malhotra','Meera Nair','Siddharth Jain','Riya Sinha','Dev Choudhary','Aditi Bansal','Kabir Khan','Nisha Reddy']
    from datetime import timedelta
    for i,name in enumerate(names,1):
        roll=f'DEMO26{i:03}'
        if Student.query.filter_by(roll=roll).first(): continue
        student=Student(roll=roll,name=name,email=f'student{i}@example.com',course='B.Tech CSE',semester=7)
        db.session.add(student); db.session.flush()
        db.session.add(Fee(student_id=student.id,total=55000,paid=[55000,40000,25000,0][i%4]))
        for j in range(10):
            day=date.today()-timedelta(days=j)
            db.session.add(Attendance(student_id=student.id,day=day,status='Absent' if (i+j)%7==0 else 'Present'))
    for d,subject in enumerate(['DevOps & Automation','Cloud Computing','Computer Networks','Software Engineering','Project Lab']):
        if not Timetable.query.filter_by(day=d,start='09:00',course='B.Tech CSE',semester=7).first():
            db.session.add(Timetable(day=d,start='09:00',end='10:00',subject=subject,room='Lab 201',course='B.Tech CSE',semester=7))
    db.session.commit(); print('Demo records ready.')
@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(409)
def error(e): return jsonify(error=e.description),e.code
@app.cli.command('init-db')
def init_db(): db.create_all()
if __name__=='__main__': app.run(port=5000)
