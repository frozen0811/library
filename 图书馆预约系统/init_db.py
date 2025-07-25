from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
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


class Seat(db.Model):
    __tablename__ = 'seats'
    id = db.Column(db.Integer, primary_key=True)
    seat_number = db.Column(db.String(10), nullable=False)
    location = db.Column(db.String(50), nullable=False)
    status = db.Column(db.Enum('available', 'reserved', 'occupied', 'unavailable'), nullable=False, default='available')
    reservation_time = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('seats', lazy=True))

def main():
    with app.app_context():
        db.drop_all()
        print("已删除旧表")

        db.create_all()
        print("已创建新表")

        admin_user = User(
            username='admin',
            password='admin',
            is_admin=True
        )

        db.session.add(admin_user)
        print(f"已创建管理员，账号：admin，密码：admin")

        seat_definitions = {'1层': 40, '2层': 70, '3层': 50}
        seats_to_create = []

        for location, count in seat_definitions.items():
            for i in range(1, count + 1):
                seat = Seat(
                    seat_number=f"{location}-{i:02d}",
                    location=location
                )
                seats_to_create.append(seat)

        db.session.add_all(seats_to_create)
        print(f"正在创建 {len(seats_to_create)} 个座位...")

        db.session.commit()
        print("管理员账户和座位数据创建成功！")
        print("数据库初始化完成！")


if __name__ == '__main__':
    main()