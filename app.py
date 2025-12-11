from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, Admin, Doctor, Patient, Appointment, Treatment, Department, DoctorAvailability
from datetime import datetime, timedelta, date
from sqlalchemy import or_, and_

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Helper function to check authentication
def login_required(role=None):
    def decorator(f):
        def wrapper(*args, **kwargs):
            if 'user_id' not in session or 'role' not in session:
                flash('Please login first', 'danger')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('Unauthorized access', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# Home and Authentication Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        user = None
        if role == 'admin':
            user = Admin.query.filter_by(username=username).first()
        elif role == 'doctor':
            user = Doctor.query.filter_by(username=username).first()
        elif role == 'patient':
            user = Patient.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if role in ['doctor', 'patient'] and not user.is_active:
                flash('Your account has been deactivated', 'danger')
                return redirect(url_for('login'))
            
            session['user_id'] = user.id
            session['role'] = role
            session['username'] = user.username
            
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        age = request.form.get('age')
        gender = request.form.get('gender')
        address = request.form.get('address')
        
        # Check if username or email already exists
        existing_patient = Patient.query.filter(
            or_(Patient.username == username, Patient.email == email)
        ).first()
        
        if existing_patient:
            flash('Username or email already exists', 'danger')
            return redirect(url_for('register'))
        
        # Normalize age so it is never negative
        if age:
            age_val = int(age)
            if age_val < 0:
                age_val = 0
        else:
            age_val = None
        
        patient = Patient(
            username=username,
            name=name,
            email=email,
            phone=phone,
             age=age_val,
            gender=gender,
            address=address
        )
        patient.set_password(password)
        
        db.session.add(patient)
        db.session.commit()
        
        flash('Registration successful! Please login', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# Admin Routes
@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    total_doctors = Doctor.query.filter_by(is_active=True).count()
    total_patients = Patient.query.filter_by(is_active=True).count()
    total_appointments = Appointment.query.count()
    
    # Upcoming appointments
    today = date.today()
    upcoming_appointments = Appointment.query.filter(
        Appointment.date >= today,
        Appointment.status == 'Booked'
    ).order_by(Appointment.date, Appointment.time).all()
    
    # Registered patients
    patients = Patient.query.filter_by(is_active=True).all()
    
    doctors = Doctor.query.filter_by(is_active=True).all()
    
    return render_template(
        'admin_dashboard.html',
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_appointments=total_appointments,
        upcoming_appointments=upcoming_appointments,
        patients=patients,
        doctors=doctors,
        search_type=None,
        search_query=''
    )


@app.route('/admin/add_doctor', methods=['GET', 'POST'])
@login_required(role='admin')
def add_doctor():
    departments = Department.query.all()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        specialization = request.form.get('specialization')
        department_id = request.form.get('department_id')
        experience = request.form.get('experience')
        
        # Check if username or email already exists
        existing_doctor = Doctor.query.filter(
            or_(Doctor.username == username, Doctor.email == email)
        ).first()
        
        if existing_doctor:
            flash('Username or email already exists', 'danger')
            return redirect(url_for('add_doctor'))
        
        exp_val = int(experience) if experience else 0
        if exp_val < 0:
            flash('Experience cannot be negative.', 'danger')
            return redirect(url_for('add_doctor'))
        
        doctor = Doctor(
            username=username,
            name=name,
            email=email,
            phone=phone,
            specialization=specialization,
            department_id=int(department_id),
            experience=exp_val
        )
        doctor.set_password(password)
        
        db.session.add(doctor)
        db.session.commit()
        
        flash('Doctor added successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    
    departments = Department.query.all()
    return render_template('add_doctor.html', departments=departments)

@app.route('/admin/update_doctor/<int:doctor_id>', methods=['GET', 'POST'])
@login_required(role='admin')
def update_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    departments = Department.query.all()
    
    if request.method == 'POST':
        doctor.name = request.form.get('name')
        doctor.email = request.form.get('email')
        doctor.phone = request.form.get('phone')
        doctor.specialization = request.form.get('specialization')
        doctor.department_id = int(request.form.get('department_id'))
        doctor.experience = int(request.form.get('experience')) if request.form.get('experience') else None
        
        db.session.commit()
        flash('Doctor updated successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('update_doctor.html', doctor=doctor, departments=departments)

@app.route('/admin/remove_doctor/<int:doctor_id>')
@login_required(role='admin')
def remove_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.is_active = False
    db.session.commit()
    flash('Doctor removed successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/remove_patient/<int:patient_id>')
@login_required(role='admin')
def remove_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.is_active = False
    db.session.commit()
    flash('Patient removed successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/view_appointments')
@login_required(role='admin')
def view_appointments():
    appointments = Appointment.query.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template('view_appointments.html', appointments=appointments)

@app.route('/admin/appointment/<int:appointment_id>/complete', methods=['GET', 'POST'])
@login_required(role='admin')
def admin_complete_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    appt.status = 'Completed'
    db.session.commit()
    return redirect(url_for('view_appointments'))


@app.route('/admin/appointment/<int:appointment_id>/cancel', methods=['GET', 'POST'])
@login_required(role='admin')
def admin_cancel_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    appt.status = 'Cancelled'
    db.session.commit()
    return redirect(url_for('view_appointments'))


@app.route('/admin/search', methods=['GET', 'POST'])
@login_required(role='admin')
def admin_search():
    search_query = ''
    search_type = 'doctor'

    doctors = []
    patients = []
    upcoming_appointments = []

    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        search_type = request.form.get('search_type', 'doctor')

        if search_type == 'doctor':
            # Find doctors by name or specialization
            doctors = Doctor.query.filter(
                or_(
                    Doctor.name.ilike(f'%{search_query}%'),
                    Doctor.specialization.ilike(f'%{search_query}%')
                )
            ).all()

            # Upcoming appointments for these doctors
            if doctors:
                doctor_ids = [d.id for d in doctors]
                upcoming_appointments = Appointment.query.filter(
                    Appointment.doctor_id.in_(doctor_ids),
                    Appointment.date >= date.today(),
                    Appointment.status == 'Booked'
                ).order_by(Appointment.date, Appointment.time).all()


        elif search_type == 'patient':
            # Find patients by name or email
            patients = Patient.query.filter(
                or_(
                    Patient.name.ilike(f'%{search_query}%'),
                    Patient.email.ilike(f'%{search_query}%')
                )
            ).all()

            # Upcoming appointments for these patients
            if patients:
                patient_ids = [p.id for p in patients]
                upcoming_appointments = Appointment.query.filter(
                    Appointment.patient_id.in_(patient_ids),
                    Appointment.date >= date.today(),
                    Appointment.status == 'Booked'
                ).order_by(Appointment.date, Appointment.time).all()


    # Render same admin dashboard template but with search results
    return render_template(
        'admin_dashboard.html',
        search_query=search_query,
        search_type=search_type,
        doctors_search_results=doctors,
        patients_search_results=patients,
        search_appointments=upcoming_appointments
    )

@app.route('/admin/doctor/<int:doctor_id>/toggle', methods=['GET', 'POST'])
@login_required(role='admin')
def toggle_doctor_status(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.is_active = not doctor.is_active
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/doctor/<int:doctor_id>/edit', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)

    if request.method == 'POST':
        doctor.name = request.form.get('name').strip()
        doctor.email = request.form.get('email').strip()
        doctor.phone = request.form.get('phone').strip()
        doctor.specialization = request.form.get('specialization').strip()
        # add other fields if your Doctor model has them

        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_doctor.html', doctor=doctor)


@app.route('/admin/patient/<int:patient_id>/toggle', methods=['GET', 'POST'])
@login_required(role='admin')
def toggle_patient_status(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.is_active = not patient.is_active
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/patient/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    if request.method == 'POST':
        patient.name = request.form.get('name').strip()
        patient.email = request.form.get('email').strip()
        patient.phone = request.form.get('phone').strip()
        # add other fields if your Patient model has them (age, address, etc.)

        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_patient.html', patient=patient)

@app.route('/admin/patient/<int:patient_id>/blacklist', methods=['GET', 'POST'])
@login_required(role='admin')
def toggle_patient_blacklist(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.is_blacklisted = not patient.is_blacklisted
    db.session.commit()
    return redirect(url_for('admin_dashboard'))



# Doctor Routes
@app.route('/doctor/dashboard')
@login_required(role='doctor')
def doctor_dashboard():
    doctor_id = session.get('user_id')
    doctor = Doctor.query.get(doctor_id)
    
    # Upcoming appointments for next 7 days
    today = date.today()
    next_week = today + timedelta(days=7)
    
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date >= today,
        Appointment.date <= next_week,
        Appointment.status == 'Booked'
    ).order_by(Appointment.date, Appointment.time).all()
    
    # List of patients assigned to doctor
    patient_ids = db.session.query(Appointment.patient_id).filter(
        Appointment.doctor_id == doctor_id
    ).distinct().all()
    patients = Patient.query.filter(Patient.id.in_([pid[0] for pid in patient_ids])).all()
    
    return render_template('doctor_dashboard.html',
                         doctor=doctor,
                         upcoming_appointments=upcoming_appointments,
                         patients=patients)

@app.route('/doctor/appointment/<int:appointment_id>/cancel', methods=['GET', 'POST'])
@login_required(role='doctor')
def doctor_cancel_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)

    # ensure this appointment belongs to the logged‑in doctor
    if appt.doctor_id != session.get('user_id'):
        flash('You are not allowed to modify this appointment.', 'danger')
        return redirect(url_for('doctor_dashboard'))

    appt.status = 'Cancelled'
    db.session.commit()
    flash('Appointment cancelled.', 'success')
    return redirect(url_for('doctor_dashboard'))


@app.route('/doctor/availability', methods=['GET', 'POST'])
@login_required(role='doctor')
def doctor_availability():
    doctor_id = session.get('user_id')

    if request.method == 'POST':
        today = date.today()
        next_week = today + timedelta(days=7)

        # Clear existing availability for next 7 days
        DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.date >= today,
            DoctorAvailability.date <= next_week
        ).delete()

        # Read values from the form and save
        for i in range(7):
            availability_date = today + timedelta(days=i)
            date_str = availability_date.strftime('%Y-%m-%d')

            is_available = request.form.get(f'available_{date_str}') == 'yes'
            start_time = request.form.get(f'start_time_{date_str}')
            end_time = request.form.get(f'end_time_{date_str}')

            if is_available and start_time and end_time:
                start_t = datetime.strptime(start_time, '%H:%M').time()
                end_t = datetime.strptime(end_time, '%H:%M').time()

                availability = DoctorAvailability(
                    doctor_id=doctor_id,
                    date=availability_date,
                    start_time=start_t,
                    end_time=end_t,
                    is_available=True
                )
                db.session.add(availability)

        db.session.commit()
        return redirect(url_for('doctor_dashboard'))

    # GET: show form
    today = date.today()
    next_week = today + timedelta(days=7)
    availabilities = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= next_week
    ).all()

    availability_dict = {avail.date: avail for avail in availabilities}
    days = [(today + timedelta(days=i)) for i in range(7)]

    return render_template(
        'doctor_availability.html',
        availability_dict=availability_dict,
        days=days
    )



@app.route('/doctor/mark_appointment/<int:appointment_id>/<status>')
@login_required(role='doctor')
def mark_appointment(appointment_id, status):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != session.get('user_id'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('doctor_dashboard'))
    
    if status in ['Completed', 'Cancelled']:
        appointment.status = status
        db.session.commit()
        flash(f'Appointment marked as {status}', 'success')
    
    return redirect(url_for('doctor_dashboard'))

@app.route('/doctor/update_treatment/<int:appointment_id>', methods=['GET', 'POST'])
@login_required(role='doctor')
def update_treatment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != session.get('user_id'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('doctor_dashboard'))
    
    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis')
        prescription = request.form.get('prescription')
        notes = request.form.get('notes')
        
        # Check if treatment already exists
        treatment = Treatment.query.filter_by(appointment_id=appointment_id).first()
        
        if treatment:
            treatment.diagnosis = diagnosis
            treatment.prescription = prescription
            treatment.notes = notes
        else:
            treatment = Treatment(
                appointment_id=appointment_id,
                diagnosis=diagnosis,
                prescription=prescription,
                notes=notes
            )
            db.session.add(treatment)
        
        # Mark appointment as completed
        appointment.status = 'Completed'
        db.session.commit()
        
        flash('Treatment updated successfully', 'success')
        return redirect(url_for('doctor_dashboard'))
    
    treatment = Treatment.query.filter_by(appointment_id=appointment_id).first()
    return render_template('update_treatment.html', appointment=appointment, treatment=treatment)

@app.route('/doctor/patient_history/<int:patient_id>')
@login_required(role='doctor')
def doctor_patient_history(patient_id):
    doctor_id = session.get('user_id')
    patient = Patient.query.get_or_404(patient_id)
    
    # Get all completed appointments with treatments for this patient with this doctor
    appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.doctor_id == doctor_id,
        Appointment.status == 'Completed'
    ).order_by(Appointment.date.desc()).all()
    
    return render_template('patient_history.html', patient=patient, appointments=appointments, user_role='doctor')

# Patient Routes
@app.route('/patient/dashboard')
@login_required(role='patient')
def patient_dashboard():
    patient_id = session.get('user_id')
    patient = Patient.query.get(patient_id)
    
    # Get doctors availability for next 7 days
    today = date.today()
    next_week = today + timedelta(days=7)
    
    availabilities = DoctorAvailability.query.filter(
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= next_week,
        DoctorAvailability.is_available == True
    ).join(Doctor).filter(Doctor.is_active == True).all()
    
    # Upcoming appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.date >= today,
        Appointment.status == 'Booked'
    ).order_by(Appointment.date, Appointment.time).all()
    
    # Past appointments
    past_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        or_(Appointment.date < today, Appointment.status.in_(['Completed', 'Cancelled']))
    ).order_by(Appointment.date.desc()).limit(10).all()

    departments = Department.query.all()
    
    return render_template('patient_dashboard.html',
                         patient=patient,
                         availabilities=availabilities,
                         upcoming_appointments=upcoming_appointments,
                         past_appointments=past_appointments,
                         departments=departments)

@app.route('/patient/edit_profile', methods=['GET', 'POST'])
@login_required(role='patient')
def edit_profile():
    patient_id = session.get('user_id')
    patient = Patient.query.get(patient_id)
    
    if request.method == 'POST':
        patient.name = request.form.get('name')
        patient.email = request.form.get('email')
        patient.phone = request.form.get('phone')
        patient.age = int(request.form.get('age')) if request.form.get('age') else None
        patient.gender = request.form.get('gender')
        patient.address = request.form.get('address')
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('patient_dashboard'))
    
    return render_template('edit_profile.html', patient=patient)

@app.route('/patient/search_doctors', methods=['GET', 'POST'])
@login_required(role='patient')
def search_doctors():
    if request.method == 'POST':
        search_query = request.form.get('search_query')
        
        doctors = Doctor.query.filter(
            or_(
                Doctor.name.ilike(f'%{search_query}%'),
                Doctor.specialization.ilike(f'%{search_query}%')
            ),
            Doctor.is_active == True
        ).all()
        
        return render_template('search_doctors.html', doctors=doctors, search_query=search_query)
    
    return render_template('search_doctors.html')

@app.route('/patient/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
@login_required(role='patient')
def book_appointment(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    patient_id = session.get('user_id')
    
    if request.method == 'POST':
        appointment_date = request.form.get('date')
        appointment_time = request.form.get('time')
        reason = request.form.get('reason')
        
        appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(appointment_time, '%H:%M').time()
        
        # If user picks a past date/time, move it to now (today, current time)
        today = date.today()
        now_dt = datetime.now()
        now_time = now_dt.time()
        
        if appointment_date < today:
            appointment_date = today
            appointment_time = now_time
        elif appointment_date == today and appointment_time <= now_time:
            appointment_time = now_time

        
        # Check if doctor is available at this time
        existing_appointment = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.date == appointment_date,
            Appointment.time == appointment_time,
            Appointment.status == 'Booked'
        ).first()
        
        if existing_appointment:
            flash('This time slot is already booked. Please choose another time.', 'danger')
            return redirect(url_for('book_appointment', doctor_id=doctor_id))
        
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            date=appointment_date,
            time=appointment_time,
            reason=reason,
            status='Booked'
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        flash('Appointment booked successfully', 'success')
        return redirect(url_for('patient_dashboard'))
    
    # Get doctor's availability for next 7 days
    today = date.today()
    next_week = today + timedelta(days=7)
    availabilities = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= next_week,
        DoctorAvailability.is_available == True
    ).all()
    
    return render_template('book_appointment.html',
                       doctor=doctor,
                       availabilities=availabilities,
                       datetime=datetime)

@app.route('/patient/cancel_appointment/<int:appointment_id>')
@login_required(role='patient')
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.patient_id != session.get('user_id'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('patient_dashboard'))
    
    appointment.status = 'Cancelled'
    db.session.commit()
    
    flash('Appointment cancelled successfully', 'success')
    return redirect(url_for('patient_dashboard'))

@app.route('/patient/appointment/<int:appointment_id>/reschedule', methods=['GET', 'POST'])
@login_required(role='patient')
def reschedule_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)

    if appt.patient_id != session.get('user_id'):
        flash('You cannot modify this appointment.', 'danger')
        return redirect(url_for('patient_dashboard'))

    if request.method == 'POST':
        new_date_str = request.form.get('date')
        new_time_str = request.form.get('time')

        new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
        new_time = datetime.strptime(new_time_str, '%H:%M').time()

        conflict = Appointment.query.filter_by(
            doctor_id=appt.doctor_id,
            date=new_date,
            time=new_time
        ).first()

        if conflict:
            flash('Doctor already has an appointment at that time.', 'danger')
            return redirect(url_for('reschedule_appointment', appointment_id=appointment_id))

        appt.date = new_date
        appt.time = new_time
        db.session.commit()
        flash('Appointment rescheduled.', 'success')
        return redirect(url_for('patient_dashboard'))

    return render_template('reschedule_appointment.html', appointment=appt)


@app.route('/patient/history')
@login_required(role='patient')
def patient_history():
    patient_id = session.get('user_id')
    patient = Patient.query.get(patient_id)
    
    # Get all completed appointments with treatments
    appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.status == 'Completed'
    ).order_by(Appointment.date.desc()).all()
    
    return render_template('patient_history.html', patient=patient, appointments=appointments, user_role='patient')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)


