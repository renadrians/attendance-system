import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, session, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class ClockInOut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    clock_type = db.Column(db.String(10), nullable=False)  # 'in' or 'out'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/', methods=['POST', 'GET'])
def index():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        if user.is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('clock_in_out'))
    return render_template('login.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        new_staff = User(username=username, password=password)
        try:
            db.session.add(new_staff)
            db.session.commit()
            return redirect(url_for('login'))  # Redirect to the staff login page after registration
        except:
            return 'There was an issue registering the staff'
    return render_template('register.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        staff = User.query.filter_by(username=username, password=password, is_admin=False).first()
        if staff:
            session['user_id'] = staff.id
            return redirect(url_for('staff_dashboard'))
        else:
            return 'Invalid staff credentials'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  # Clear the session to log the user out
    return redirect(url_for('index'))


@app.route('/staff_dashboard')
def staff_dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        return render_template('staff_dashboard.html', user=user)
    return redirect('/')


@app.route('/clock-in-out', methods=['GET', 'POST'])
def clock_in_out():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        if request.method == 'POST':
            clock_type = request.form['clock_type']
            new_clock = ClockInOut(user_id=user_id, clock_type=clock_type)
            
            with app.app_context():
                db.session.add(new_clock)
                db.session.commit()
            
        clocks = ClockInOut.query.filter_by(user_id=user_id).order_by(ClockInOut.timestamp.desc()).all()
        return render_template('clock_in_out.html', user=user, clocks=clocks, greeting=f"Hello, {user.username}")
    return redirect('/')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        if request.method == 'POST':
            new_username = request.form['new_username']
            new_password = request.form['new_password']

            # Update user profile
            user.username = new_username

            # Only update password if a new password is provided
            if new_password:
                user.password = new_password

            try:
                db.session.commit()
                return redirect(url_for('profile'))
            except:
                return 'There was an issue updating your profile'
        return render_template('profile.html', user=user)
    return redirect('/')


@app.route('/history', methods=['GET', 'POST'])
def history():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        clocks = ClockInOut.query.filter_by(user_id=user_id).order_by(ClockInOut.timestamp.desc()).all()
        return render_template('history.html', user=user, clocks=clocks)
    return redirect('/')

@app.route('/export-history', methods=['GET'])
def export_history():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        clocks = ClockInOut.query.filter_by(user_id=user_id).order_by(ClockInOut.timestamp.desc()).all()

        # Export clocks to a CSV file
        filename = f"{user.username}_history.csv"
        with open(filename, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            
            # Write the header row
            csv_writer.writerow(['Timestamp', 'Clock Type'])
            
            # Write clock-in and clock-out data
            for clock in clocks:
                csv_writer.writerow([clock.timestamp, clock.clock_type])

        return send_file(filename, as_attachment=True)
    return redirect('/')




@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        new_admin = User(username=username, password=password, is_admin=True)
        try:
            db.session.add(new_admin)
            db.session.commit()
            return redirect(url_for('admin_login'))  # Redirect to the admin login page after registration
        except:
            return 'There was an issue registering the admin'
    return render_template('admin_register.html')


@app.route('/admin_clock_in_out', methods=['GET', 'POST'])
def admin_clock_in_out():
    if 'user_id' in session:
        user_id = session['user_id']
        admin = User.query.get(user_id)
        if admin.is_admin:
            if request.method == 'POST':
                clock_type = request.form['clock_type']
                new_clock = ClockInOut(user_id=user_id, clock_type=clock_type)
                with app.app_context():
                    db.session.add(new_clock)
                    db.session.commit()
            clocks = ClockInOut.query.filter_by(user_id=user_id).order_by(ClockInOut.timestamp.desc()).all()
            return render_template('admin_clock_in_out.html', admin=admin, clocks=clocks)
    return redirect('/')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = User.query.filter_by(username=username, password=password, is_admin=True).first()
        if admin:
            session['user_id'] = admin.id
            return redirect(url_for('admin_dashboard'))
        else:
            return 'Invalid admin credentials'
    return render_template('admin_login.html')


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' in session:
        admin_id = session['user_id']
        admin = User.query.get(admin_id)
        if admin.is_admin:
            users = User.query.all()
            return render_template('admin_dashboard.html', admin=admin, users=users)
    return redirect('/')

@app.route('/edit_staff', methods=['GET', 'POST'])
def edit_staff():
    if 'user_id' in session:
        admin_id = session['user_id']
        admin = User.query.get(admin_id)
        if admin.is_admin:
            if request.method == 'POST':
                # Handle staff editing logic
                staff_id = int(request.form['staff_id'])
                new_username = request.form['new_username']
                new_password = request.form['new_password']
                
                staff = User.query.get(staff_id)
                if staff:
                    staff.username = new_username
                    if new_password:
                        staff.password = new_password
                    try:
                        db.session.commit()
                        return redirect(url_for('edit_staff'))
                    except:
                        return 'There was an issue updating the staff profile'

            staffs = User.query.filter_by(is_admin=False).all()
            return render_template('edit_staff.html', admin=admin, staffs=staffs)
    return redirect('/')

@app.route('/add_staff', methods=['GET', 'POST'])
def add_staff():
    if 'user_id' in session:
        admin_id = session['user_id']
        admin = User.query.get(admin_id)
        if admin.is_admin:
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                new_staff = User(username=username, password=password)
                try:
                    db.session.add(new_staff)
                    db.session.commit()
                    return redirect(url_for('edit_staff'))
                except:
                    return 'There was an issue adding the staff'
            return render_template('add_staff.html', admin=admin)
    return redirect('/')




@app.route('/delete_staff/<int:staff_id>')
def delete_staff(staff_id):
    if 'user_id' in session:
        admin_id = session['user_id']
        admin = User.query.get(admin_id)
        if admin.is_admin:
            staff = User.query.get(staff_id)
            if staff:
                try:
                    db.session.delete(staff)
                    db.session.commit()
                except:
                    pass
            return redirect(url_for('edit_staff'))
    return redirect('/')

@app.route('/admin_profile', methods=['GET', 'POST'])
def admin_profile():
    if 'user_id' in session:
        admin_id = session['user_id']
        admin = User.query.get(admin_id)
        if request.method == 'POST':
            new_username = request.form['new_username']
            new_password = request.form['new_password']

            # Update admin profile
            admin.username = new_username

            # Only update password if a new password is provided
            if new_password:
                admin.password = new_password

            try:
                db.session.commit()
                return redirect(url_for('admin_profile'))
            except:
                return 'There was an issue updating your profile'
        return render_template('admin_edit_profile.html', admin=admin)
    return redirect('/')


@app.route('/admin_history', methods=['GET'])
def admin_history():
    if 'user_id' in session:
        admin_id = session['user_id']
        admin = User.query.get(admin_id)
        if admin.is_admin:
            clocks = ClockInOut.query.order_by(ClockInOut.timestamp.desc()).all()
            return render_template('admin_history.html', admin=admin, clocks=clocks)
    return redirect('/')

@app.route('/admin_export_history', methods=['GET'])
def admin_export_history():
    if 'user_id' in session:
        admin_id = session['user_id']
        admin = User.query.get(admin_id)
        if admin.is_admin:
            clocks = ClockInOut.query.order_by(ClockInOut.timestamp.desc()).all()
            filename = f"admin_combined_history.csv"
            with open(filename, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['Timestamp', 'Clock Type'])
                for clock in clocks:
                    csv_writer.writerow([clock.timestamp, clock.clock_type])
            return send_file(filename, as_attachment=True)
    return redirect('/')



if __name__ == "__main__":
    app.run(debug=True)
