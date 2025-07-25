from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_changed'
password = input('请输入数据库密码：')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://root:{password}@localhost/library_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {'id': self.id, 'username': self.username, 'is_admin': self.is_admin}


class Seat(db.Model):
    __tablename__ = 'seats'
    id = db.Column(db.Integer, primary_key=True)
    seat_number = db.Column(db.String(10), nullable=False)
    location = db.Column(db.String(50), nullable=False)
    status = db.Column(db.Enum('available', 'reserved', 'occupied', 'unavailable'), nullable=False, default='available')
    reservation_time = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('seats', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'seat_number': self.seat_number,
            'location': self.location,
            'status': self.status,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'reservation_time': self.reservation_time.isoformat() if self.reservation_time else None
        }


def cleanup_expired_reservations():
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    expired_seats = Seat.query.filter(Seat.status == 'reserved', Seat.reservation_time < one_hour_ago).all()

    if expired_seats:
        for seat in expired_seats:
            seat.status = 'available'
            seat.reservation_time = None
            seat.user_id = None
        db.session.commit()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            return redirect(url_for('login', admin_login=True))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('用户名已存在!', 'error')
            return redirect(url_for('register'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)

        db.session.commit()
        flash('注册成功，请登录!', 'success')
        return redirect(url_for('login'))

    return render_template('login_register.html', is_register=True)


@app.route('/login', methods=['GET', 'POST'])
def login():
    is_admin_login = request.args.get('admin_login')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            if is_admin_login and not user.is_admin:
                flash('非管理员账户!', 'error')
                return redirect(url_for('login', admin_login=True))
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin

            if user.is_admin:
                return redirect(url_for('admin_reservations'))
            return redirect(url_for('index'))

        else:
            flash('用户名或密码错误!', 'error')
    return render_template('login_register.html', is_admin_login=is_admin_login)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/reservations')
@admin_required
def admin_reservations():
    return render_template('admin_reservations.html')

@app.route('/admin/accounts')
@admin_required
def admin_accounts():
    return render_template('admin_accounts.html')

@app.route('/api/seats/<int:floor>')
def get_seats_by_floor(floor):
    cleanup_expired_reservations()
    seats = Seat.query.filter_by(location=f'{floor}层').all()
    my_seat_id = None

    if 'user_id' in session:
        my_seat_obj = Seat.query.filter_by(user_id=session['user_id']).filter(
            Seat.status.in_(['reserved', 'occupied'])).first()
        
        if my_seat_obj:
            my_seat_id = my_seat_obj.id

    seat_list = [seat.to_dict() for seat in seats]
    return jsonify({'seats': seat_list, 'my_seat_id': my_seat_id})


@app.route('/api/reserve/<int:seat_id>', methods=['POST'])
@login_required
def reserve_seat(seat_id):
    user_id = session['user_id']

    if Seat.query.filter_by(user_id=user_id).filter(Seat.status.in_(['reserved', 'occupied'])).first():
        return jsonify({'success': False, 'message': '您已有一个座位，不能重复预约'}), 400
    seat = Seat.query.get(seat_id)

    if not seat or seat.status != 'available':
        return jsonify({'success': False, 'message': '该座位不可预约'}), 400
    seat.status = 'reserved'
    seat.reservation_time = datetime.utcnow()
    seat.user_id = user_id

    db.session.commit()
    return jsonify({'success': True, 'message': '座位预约成功！请在1小时内入座，否则预约将被取消。'})


@app.route('/api/release/<int:seat_id>', methods=['POST'])
@login_required
def release_seat(seat_id):
    seat = Seat.query.get(seat_id)

    if not seat or seat.user_id != session['user_id']:
        return jsonify({'success': False, 'message': '无效操作'}), 403
    seat.status = 'available'
    seat.reservation_time = None
    seat.user_id = None

    db.session.commit()
    return jsonify({'success': True, 'message': '座位已成功释放'})


@app.route('/api/admin/seat/status/<int:seat_id>', methods=['POST'])
@admin_required
def admin_update_seat_status(seat_id):
    new_status = request.json.get('status')
    valid_statuses = ['available', 'reserved', 'occupied', 'unavailable']
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'message': '无效的状态值'}), 400
    seat = Seat.query.get(seat_id)
    
    if not seat:
        return jsonify({'success': False, 'message': '座位不存在'}), 404

    seat.status = new_status
    if new_status in ['available', 'unavailable']:
        seat.reservation_time = None
        seat.user_id = None
    
    elif new_status == 'occupied':
        seat.reservation_time = None
        if seat.user_id is None:
            seat.user_id = session['user_id']
    
    elif new_status == 'reserved':
        seat.reservation_time = datetime.utcnow()
        if seat.user_id is None:
            seat.user_id = session['user_id']

    db.session.commit()
    return jsonify({'success': True, 'message': '座位状态更新成功！'})


@app.route('/api/admin/users')
@admin_required
def get_users():
    users = User.query.filter_by(is_admin=False).all()
    return jsonify([user.to_dict() for user in users])


@app.route('/api/admin/users/delete/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    if user.is_admin:
        return jsonify({'success': False, 'message': '不能删除管理员账户'}), 403
    Seat.query.filter_by(user_id=user_id).update({
        'status': 'available',
        'reservation_time': None,
        'user_id': None
    })
    db.session.delete(user)

    db.session.commit()
    return jsonify({'success': True, 'message': '用户已删除'})


if __name__ == '__main__':
    app.run(debug=True)