from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from datetime import datetime, timezone, timedelta
from flask import send_from_directory
import uuid
import json
from sqlalchemy import func
from datetime import datetime, time
from calendar import monthrange
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from sqlalchemy import text




cloudinary.config(
    cloud_name = "dhm1xd1di",  # اسم الـ Cloud الخاص بك
    api_key = "878343572856269",        # مفتاح الـ API
    api_secret = "zBqp8DKLdL3A8099tTiiLN_iRgM",  # سر الـ API الخاص بك
    secure=True
)

# إعداد التطبيق
app = Flask(__name__)
app.permanent_session_lifetime = timedelta(days=365*100)  # تعيين مدة الجلسة لتكون طويلة (100 سنة)

# تعيين مفتاح سري للجلسة
app.config['SECRET_KEY'] = 'b6d5a2c1e44a5a8f9dc52b0a3e5f2e4b3d56f7cfe7c3a6b5c6c7d8e9f0a1b2c3'


# تمكين CORS لدعم الطلبات من الـ frontend
CORS(app, supports_credentials=True, origins=["https://points-almohtarif.netlify.app"])
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
  
# إعداد الاتصال بقاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:mMrWeYBCubaLDrTbQLXpVPvwrwoEAfrM@switchback.proxy.rlwy.net:46042/railway'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'connect_args': {
        'connect_timeout': 30
    }
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads', 'images')
db = SQLAlchemy(app)
    
def parse_timestamp(timestamp):
    if timestamp.endswith("Z"):
        # إذا كان الوقت يحتوي على Z، فإننا نحذفه ونقوم بتحويله إلى وقت UTC
        return datetime.strptime(timestamp[:-1], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)  # تحويل الوقت إلى datetime UTC
    else:
        # إذا لم يحتوي على "Z"، نقوم بتفسيره باستخدام fromisoformat مع إضافة المنطقة الزمنية المحلية
        return datetime.fromisoformat(timestamp) # إذا لم يكن يحتوي على Z، نستخدم fromisoformat بشكل طبيعي

# تحديد مسار تخزين الصور
image_folder = 'uploads/images'

# تحقق إذا كان المجلد موجودًا، وإذا لم يكن، قم بإنشائه
if not os.path.exists(image_folder):
    os.makedirs(image_folder)

class OperationsEmployee(db.Model):
    __tablename__ = 'operations_employees'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=True)
    
    evaluation_id = db.Column(db.Integer, db.ForeignKey('evaluations.id', ondelete='CASCADE'), nullable=True)

    notification_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.Boolean, default=False)  # غير مقروء
    
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # علاقات
    employee = db.relationship("Employee", foreign_keys=[employee_id])
    supervisor = db.relationship("Employee", foreign_keys=[supervisor_id])
    evaluation = db.relationship("Evaluation", foreign_keys=[evaluation_id])

# تعريف جدول الموظفين في قاعدة البيانات
class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    department = db.Column(db.String(100))
    name = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True, nullable=False)
    position = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    points = db.Column(db.Integer, default=0)  # النقاط الافتراضية تكون 0


# تعريف جدول التقييمات في قاعدة البيانات
class Evaluation(db.Model):
    __tablename__ = 'evaluations'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)#id
    employee_name = db.Column(db.String(100))#اسم الموظف
    client_name = db.Column(db.String(100))#اسم العميل
    service_type = db.Column(db.String(100))#نوع الخدمة
    evaluation_type = db.Column(db.String(100))#نوع التقييم
    client_consent = db.Column(db.String(100))#الموافقة من قبل العميل (نعم او لا)
    consent_link = db.Column(db.String(255), nullable=True)# لينك في حال كان نعم 
    notes = db.Column(db.Text, nullable=True)#ملاحظات الموظف
    operations_employee = db.Column(db.String(100))# اسم موظف العمليات
    operations_evaluation = db.Column(db.String(10))  # تقييم موظف العمليات
    image_path = db.Column(db.String(512), nullable=True) #مسار الصورة المرسلة من قبل الموظف 
    status = db.Column(db.String(50), nullable=True)  # عمود مقبول مرفوض قيد المراجعة  status
    created_at = db.Column(db.DateTime)#توقيت ارسال الفورم من الموظف
    supervisor_note = db.Column(db.String(500), nullable=True)  # ملاحظة المشرف الجديدة
    # اسم المشرف
    supervisor_name = db.Column(db.String(100), nullable=True)
    # توقيت الإجراء من المشرف)
    supervisor_action_time = db.Column(db.DateTime, nullable=True) 
    points = db.Column(db.Integer, nullable=True)  # هذا عمود النقاط المحسوبة لكل تقييم

class EvaluationCriteria(db.Model):
    __tablename__ = 'evaluation_criteria'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    evaluation_type = db.Column(db.String, nullable=False)
    value = db.Column(db.Integer, nullable=False) # وقت إجراء المشرف
#دالة للاشعارات للموظف
def create_notification_for_employee(evaluation, status):
    status_text = 'قبول' if evaluation.status == 'مقبول' else 'رفض'
    message = f"تم {status_text} التقييم الخاص بك من قبل المشرف {evaluation.supervisor_name}"
    employee = Employee.query.filter_by(name=evaluation.employee_name).first()
    supervisor = Employee.query.filter_by(name=evaluation.supervisor_name).first() if evaluation.supervisor_name else None
    
    notification = Notification(
        employee_id=employee.id if employee else None,
        supervisor_id=supervisor.id if supervisor else None,
        evaluation_id=evaluation.id,
        notification_type=f"تقييم {status}",
        message=message,
        status=False  # غير مقروء
    )
    
    db.session.add(notification)
    #db.session.commit()
@app.route('/')
def index():
    return "✅ Flask backend is working on Render!"
@app.route('/test-db')
def test_db():
    try:
        db.session.execute(text('SELECT 1'))
        return 'Database connection successful!'
    except Exception as e:
        return f'Database connection failed: {str(e)}'

@app.route('/api/employee-notifications', methods=['GET'])
def get_notifications():
    try:
        # الحصول على employee_id من الجلسة
        employee_id = session.get('user_id')

        # التأكد من وجود employee_id في الجلسة
        if not employee_id:
            return jsonify({"message": "لم يتم تحديد المستخدم"}), 400

        # استعلام للحصول على الإشعارات التي لم تتم قراءتها
        notifications = Notification.query.filter_by(employee_id=employee_id, status=False).all()

        # تحويل الإشعارات إلى قائمة من القواميس
        notifications_list = [{
            'id': notification.id,
            'message': notification.message,
            'created_at': notification.created_at,
            'evaluation_id': notification.evaluation_id,
            'status': notification.status
        } for notification in notifications]

        return jsonify({"notifications": notifications_list}), 200

    except Exception as e:
        return jsonify({"message": f"حدث خطأ: {str(e)}"}), 500

@app.route('/api/mark-notification-read/<int:notification_id>', methods=['PUT'])
def mark_notification_as_read(notification_id):
    try:
        # الحصول على الإشعار من قاعدة البيانات
        notification = Notification.query.get(notification_id)
        if not notification:
            return jsonify({"message": "الإشعار غير موجود"}), 404

        # التحقق من وجود employee_id في الجلسة والتأكد من أنه نفس الموظف المرتبط بالإشعار
        employee_id = session.get('user_id')
        if not employee_id:
            return jsonify({"message": "لم يتم تحديد المستخدم. يرجى تسجيل الدخول."}), 400

        if notification.employee_id != employee_id:
            return jsonify({"message": "لا يمكنك تحديث إشعار موظف آخر."}), 403

        # تحديث حالة الإشعار إلى "تم قراءته"
        notification.status = True
        db.session.commit()

        return jsonify({"message": "تم تحديث حالة الإشعار إلى تم قراءته"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"حدث خطأ: {str(e)}"}), 500


@app.route('/api/new-evaluations', methods=['GET'])
def get_new_evaluations():
    # استرجاع التقييمات التي هي قيد المراجعة فقط
    evaluations = Evaluation.query.filter(Evaluation.status == 'قيد المراجعة').all()
    # تحويل التقييمات إلى قائمة من القيم التي تحتاجها الإشعارات
    notifications = [
        {
            "employee_name": eval.employee_name,
            "evaluation_id": eval.id,  # يمكنك إضافة id التقييم هنا
            "created_at": eval.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        for eval in evaluations
    ]
    return jsonify(notifications)

@app.route('/api/accepted-evaluations-points-daily', methods=['GET'])
def accepted_evaluations_points_daily():
    from sqlalchemy import cast, Date, func

    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if date_from and date_to:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

            # الحصول على عدد التقييمات ومجموع النقاط حسب التاريخ
            result = db.session.query(
                cast(Evaluation.created_at, Date).label('eval_date'),
                func.count(Evaluation.id).label('num_evaluations'),
                func.sum(Evaluation.points).label('total_points')
            ).filter(
                Evaluation.status == 'مقبول',
                Evaluation.points != None,
                Evaluation.created_at >= date_from_obj,
                Evaluation.created_at <= date_to_obj
            ).group_by('eval_date').order_by('eval_date').all()

            # تحضير البيانات حسب التاريخ
            distribution = {}
            for row in result:
                date_str = str(row[0])
                num_evaluations = row[1]
                total_points = row[2]

                distribution[date_str] = {'num_evaluations': num_evaluations, 'total_points': total_points}

            return jsonify(distribution)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        return jsonify({'error': 'Both date_from and date_to are required'}), 400


@app.route('/api/evaluations-daily-stats', methods=['GET'])
def evaluations_daily_stats():
    from sqlalchemy import cast, Date

    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if date_from and date_to:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

            statuses = ['مقبول', 'مرفوض', 'قيد المراجعة']
            result = {}

            for status in statuses:
                daily_counts = db.session.query(
                    cast(Evaluation.created_at, Date).label('eval_date'),
                    func.count(Evaluation.id)
                ).filter(
                    Evaluation.created_at >= date_from_obj,
                    Evaluation.created_at <= date_to_obj,
                    Evaluation.status == status
                ).group_by('eval_date').order_by('eval_date').all()

                result[status] = {str(row[0]): row[1] for row in daily_counts}

            return jsonify(result)

        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        return jsonify({'error': 'Both date_from and date_to are required'}), 400

@app.route('/api/all-employees-scores', methods=['GET'])
def get_all_employees_scores():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if date_from and date_to:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)

            query = db.session.query(
                Evaluation.employee_name,
                func.sum(Evaluation.points).label('total_points'),
                func.count(Evaluation.id).label('total_reviews')
            ).filter(
                Evaluation.created_at >= date_from_obj,
                Evaluation.created_at <= date_to_obj
            ).group_by(
                Evaluation.employee_name
            ).order_by(
                func.sum(Evaluation.points).desc()
            )

            all_employees = query.all()
            employees_data = [{
                'employee_name': emp[0],
                'total_points': emp[1],
                'total_reviews': emp[2]
            } for emp in all_employees]

            return jsonify(employees_data)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        return jsonify({'error': 'Both date_from and date_to are required'}), 400

@app.route('/api/evaluation-type-counts')
def evaluation_type_counts():
    # جلب التاريخ من الـ query parameters
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')
    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
    except Exception as e:
        return jsonify({'error': 'صيغة التاريخ غير صحيحة، استخدم YYYY-MM-DD'}), 400

    # استعلام التقييمات بحسب نوعها ضمن النطاق الزمني
    results = db.session.query(
        Evaluation.evaluation_type,
        func.count(Evaluation.id)
    ).filter(
        Evaluation.created_at >= date_from,
        Evaluation.created_at <= date_to
    ).group_by(Evaluation.evaluation_type).all()

    # تنسيق البيانات
    labels = [row[0] or "غير محدد" for row in results]
    counts = [row[1] for row in results]

    return jsonify({
        'labels': labels,
        'counts': counts
    })
    # Route لتحصيل التقييمات والنجوم حسب موظفي العمليات
@app.route('/api/operations-stars-evaluations', methods=['GET'])
def get_operations_stars_evaluations():
    # الحصول على التواريخ من الـ frontend
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # تحويل التواريخ إلى كائنات datetime
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # جلب مجموع النجوم لكل موظف خلال الفترة المحددة
    results = db.session.query(
        Evaluation.operations_employee,
        func.sum(Evaluation.operations_evaluation).label('total_stars')
    ).filter(
        Evaluation.created_at >= start_date,
        Evaluation.created_at <= end_date,
        Evaluation.operations_evaluation.in_([1, 2, 3, 4, 5])  # لا حاجة لسلاسل نصية
    ).group_by(
        Evaluation.operations_employee
    ).order_by(
        desc('total_stars')
    ).all()
    
    # تنظيم البيانات للإرجاع فقط بدون الفترة
    employees = [{
        'name': r.operations_employee,
        'total_stars': r.total_stars
    } for r in results]
    
    return jsonify(employees)
# Route لتحصيل التقييمات المرسلة حسب التاريخ لموظفي العمليات
@app.route('/api/history-operations-evaluations', methods=['GET'])
def get_history_operations_evaluations():
    # الحصول على التواريخ من الـ frontend
    start_date = request.args.get('start_date')  # على سبيل المثال: '2025-01-01'
    end_date = request.args.get('end_date')      # على سبيل المثال: '2025-04-01'

    # تحويل التواريخ إلى كائنات datetime
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')

    # الحصول على التقييمات لموظفي العمليات ضمن هذا النطاق الزمني
    results = db.session.query(
        Evaluation.operations_employee,  # اسم موظف العمليات
        func.count(Evaluation.id).label('total_evaluations')  # عدد التقييمات
    ).filter(
        Evaluation.created_at >= start_date,
        Evaluation.created_at <= end_date
    ).group_by(
        Evaluation.operations_employee  # تجميع التقييمات حسب اسم الموظف
    ).all()

    # ترتيب البيانات في شكل مناسب لعرضها في الـ frontend
    operations_data = [
        {
            'operations_employee': result.operations_employee,  # اسم موظف العمليات
            'total_evaluations': result.total_evaluations  # عدد التقييمات
        } for result in results
    ]

    # إرجاع النتائج بتنسيق JSON
    return jsonify(operations_data)
@app.route('/api/last-3-months-stats', methods=['GET'])
def get_last_3_months_stats():
    today = datetime.now()
    results = []

    # نحسب الأشهر الثلاثة الأخيرة (تشمل الشهر الحالي)
    for i in range(2, -1, -1):
        month_date = today - timedelta(days=i*30)  # تقريبي ولكن فعّال
        year = month_date.year
        month = month_date.month

        # تحديد بداية ونهاية الشهر
        month_start = datetime(year, month, 1)
        if i == 0:  # الشهر الحالي، نأخذ لحد اليوم فقط
            month_end = today
        else:  # الأشهر السابقة، نأخذ حتى نهاية الشهر
            if month == 12:
                month_end = datetime(year + 1, 1, 1)
            else:
                month_end = datetime(year, month + 1, 1)

        # حساب عدد التقييمات لهذا الشهر
        total = db.session.query(func.count(Evaluation.id)).filter(
            Evaluation.created_at >= month_start,
            Evaluation.created_at < month_end
        ).scalar()

        # متوسط النقاط المقبولة فقط
        avg_points = db.session.query(func.avg(Evaluation.points)).filter(
            Evaluation.created_at >= month_start,
            Evaluation.created_at < month_end,
            Evaluation.status == 'مقبول',
            Evaluation.points != None
        ).scalar()

        results.append({
            'month': f'{month}/{year}',
            'total_evaluations': total,
            'avg_accepted_points': round(avg_points or 0, 2)
        })

    return jsonify(results)
@app.route('/api/service-type-distribution', methods=['GET'])
def service_type_distribution():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
   
    if not date_from or not date_to:
        return jsonify({'error': 'Both date_from and date_to are required.'}), 400
   
    try:
        # تحويل التواريخ مع مراعاة الوقت
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
       
        # استعلام أكثر كفاءة
        query = db.session.query(
            Evaluation.service_type,
            func.count(Evaluation.id).label('count')
        ).filter(
            Evaluation.created_at.between(date_from_obj, date_to_obj)
        ).group_by(Evaluation.service_type)
       
        service_data = query.all()
        total = sum(item.count for item in service_data)
       
        # إضافة نوع "غير معروف" إذا كان العدد الكلي صفر
        if not service_data and total == 0:
            return jsonify([{
                "service_type": "لا يوجد بيانات",
                "count": 0,
                "percentage": 0
            }])
       
        distribution = [{
            "service_type": item.service_type or "غير معروف",
            "count": item.count,
            "percentage": round((item.count / total) * 100, 2) if total > 0 else 0
        } for item in service_data]
       
        return jsonify(distribution)
       
    except ValueError as e:
        return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
    except Exception as e:
        app.logger.error(f'Error in service_type_distribution: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500
@app.route('/api/best-employees-homepage', methods=['GET'])
def get_best_employees_home():
    try:
        now = datetime.now()

        # تحديد بداية الشهر
        date_from_obj = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # تحديد نهاية الشهر
        if now.month == 12:  # لو ديسمبر، الشهر القادم هو يناير والسنة تزيد 1
            next_month = now.replace(year=now.year+1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month+1, day=1)

        date_to_obj = next_month - timedelta(seconds=1)  # نهاية الشهر الحالي 23:59:59

        # بدء استعلام SQLAlchemy للحصول على أفضل 5 موظفين بناءً على النقاط
        query = db.session.query(
            Evaluation.employee_name,
            func.sum(Evaluation.points).label('total_points'),
            func.count(Evaluation.id).label('total_reviews')
        )

        # إضافة شروط التصفية بناءً على بداية ونهاية الشهر الحالي
        query = query.filter(Evaluation.created_at >= date_from_obj)
        query = query.filter(Evaluation.created_at <= date_to_obj)

        # تجميع النتائج حسب اسم الموظف وترتيبها
        top_employees = query.group_by(Evaluation.employee_name) \
                             .order_by(func.sum(Evaluation.points).desc()) \
                             .limit(5).all()

        # تجهيز الرد
        employees_data = [{'employee_name': employee[0], 'total_points': employee[1], 'total_reviews': employee[2]} for employee in top_employees]

        return jsonify(employees_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/api/best-employees', methods=['GET'])
def get_best_employees():
    # الحصول على تواريخ البداية والنهاية من المعاملات المرسلة من frontend
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # التحقق من أن المعاملات موجودة وأنها صالحة
    if date_from and date_to:
        try:
            # تحويل التواريخ إلى كائنات datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')

            # إضافة 23:59:59 لتاريخ النهاية لضمان احتساب كامل اليوم
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)

            # بدء استعلام SQLAlchemy للحصول على أفضل 5 موظفين بناءً على النقاط
            query = db.session.query(
                Evaluation.employee_name,
                func.sum(Evaluation.points).label('total_points'),
                func.count(Evaluation.id).label('total_reviews')  # حساب عدد التقييمات         
            )

            # إضافة شروط التصفية بناءً على التاريخ
            query = query.filter(Evaluation.created_at >= date_from_obj)
            query = query.filter(Evaluation.created_at <= date_to_obj)

            # تجميع النتائج حسب اسم الموظف وترتيبها حسب النقاط الإجمالية
            top_employees = query.group_by(Evaluation.employee_name) \
                                 .order_by(func.sum(Evaluation.points).desc()) \
                                 .limit(5).all()

            # تحويل النتائج إلى شكل مناسب للرد
            employees_data = [{'employee_name': employee[0], 'total_points': employee[1],'total_reviews': employee[2]} for employee in top_employees]

            return jsonify(employees_data)

        except ValueError:
            return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400
    else:
        return jsonify({'error': 'Both date_from and date_to are required.'}), 400

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    # استرجاع المعايير من الاستعلام
    employee_name = request.args.get('employee_name')
    service_type = request.args.get('service_type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # بناء الاستعلام بناءً على المعايير
    query = Evaluation.query

    if employee_name:
        query = query.filter(Evaluation.employee_name.contains(employee_name))
    
    if service_type:
        query = query.filter(Evaluation.service_type.contains(service_type))
    
    if date_from:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
        # تعيين التاريخ إلى بداية اليوم (00:00:00)
        date_from_obj = datetime.combine(date_from_obj, time.min)
        query = query.filter(Evaluation.created_at >= date_from_obj)
    
    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
        # تعيين التاريخ إلى نهاية اليوم (23:59:59)
        date_to_obj = datetime.combine(date_to_obj, time.max)
        query = query.filter(Evaluation.created_at <= date_to_obj)

    # الحصول على النتائج
    evaluations = query.all()

    # تحويل البيانات إلى صيغة JSON
    evaluations_data = [
        {
            'id': evaluation.id,
            'employee_name': evaluation.employee_name,
            'client_name': evaluation.client_name,
            'service_type': evaluation.service_type,
            'evaluation_type': evaluation.evaluation_type,
            'client_consent': evaluation.client_consent,
            'consent_link': evaluation.consent_link,
            'notes': evaluation.notes,
            'operations_employee': evaluation.operations_employee,
            'operations_evaluation': evaluation.operations_evaluation,
            'image_path': evaluation.image_path,
            'status': evaluation.status,
            'created_at': evaluation.created_at.strftime('%Y-%m-%d %H:%M:%S') if evaluation.created_at else None,
            'supervisor_note': evaluation.supervisor_note,
            'supervisor_name': evaluation.supervisor_name,
            'supervisor_action_time': evaluation.supervisor_action_time.strftime('%Y-%m-%d %H:%M:%S') if evaluation.supervisor_action_time else None,
            'points': evaluation.points
        }
        for evaluation in evaluations
    ]
    
    return jsonify(evaluations_data)

@app.route('/api/service-types', methods=['GET'])
def get_service_types():
    service_types = db.session.query(Evaluation.service_type).distinct().all()  # الحصول على أنواع الخدمة المميزة من التقييمات
    service_type_data = [{'id': service_type[0], 'type': service_type[0]} for service_type in service_types]
    return jsonify(service_type_data)
@app.route('/api/employees-name', methods=['GET'])
def get_employees_name():
    employees = db.session.query(Employee).filter(Employee.position == 'موظف').all()
    employee_data = [{'id': employee.id, 'name': employee.name} for employee in employees]
    return jsonify(employee_data)
@app.route('/api/admin-dashboard-stats', methods=['GET'])
def get_admin_dashboard_stats():
    try:
        # تحقق من محتويات الجلسة
        print("Session Data:", session)
        
        # التحقق من وجود user_role في الجلسة
        user_role = session.get('user_role')
        print("User Role:", user_role)  # طباعة قيمة user_role للتأكد من صحتها

        if 'user_role' not in session or session['user_role'] not in ['مشرف', 'مدير', 'مراقب', 'سوبر ادمن']:
            return jsonify({"message": "غير مصرح"}), 403

        # باقي الكود كما هو
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)

        # حساب الإحصائيات
        employee_count = Employee.query.filter_by(position='موظف').count()
        supervisor_count = Employee.query.filter_by(position='مشرف').count()
        monitor_count = Employee.query.filter_by(position='مراقب').count()
        monthly_evaluations_count = Evaluation.query.filter(Evaluation.created_at >= start_of_month).count()
        under_review_count = Evaluation.query.filter(
            Evaluation.status == 'قيد المراجعة',
            Evaluation.created_at >= start_of_month
        ).count()

        best_employee = db.session.query(
            Evaluation.employee_name,
            func.sum(Evaluation.points).label('total_points')
        ).filter(
            Evaluation.status == 'مقبول',
            Evaluation.created_at >= start_of_month
        ).group_by(Evaluation.employee_name).order_by(func.sum(Evaluation.points).desc()).first()

        best_employee_name = best_employee.employee_name if best_employee else None
        best_employee_points = int(best_employee.total_points) if best_employee and best_employee.total_points is not None else 0

        return jsonify({
            "employee_count": employee_count,
            "supervisor_count": supervisor_count,
            "monitor_count": monitor_count,
            "monthly_evaluations_count": monthly_evaluations_count,
            "under_review_count": under_review_count,
            "best_employee": {
                "name": best_employee_name,
                "points": best_employee_points
            },
            "month": now.strftime("%B %Y")
        }), 200

    except Exception as e:
        print(f"Error: {e}")  # طباعة الاستثناء للتشخيص
        return jsonify({"error": str(e)}), 500
@app.route('/api/employee-monthly-summary', methods=['GET'])
def get_employee_monthly_summary():
    try:
        if 'user_name' not in session:
            return jsonify({"message": "يجب تسجيل الدخول أولاً"}), 401

        employee_name = session.get('user_name')
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)
        end_of_month = datetime(now.year, now.month, monthrange(now.year, now.month)[1], 23, 59, 59)

        evaluations = Evaluation.query.filter(
            Evaluation.employee_name == employee_name,
            Evaluation.created_at >= start_of_month,
            Evaluation.created_at <= end_of_month
        ).all()

        total_points = sum((e.points if e.points is not None else 0) for e in evaluations if e.status == 'مقبول')
        total_sent = len(evaluations)
        total_accepted = sum(1 for e in evaluations if e.status == 'مقبول')
        total_pending = sum(1 for e in evaluations if e.status == 'قيد المراجعة')

        return jsonify({
            "employee": employee_name,
            "total_points": int(total_points) if total_points else 0,
            "total_sent": int(total_sent),
            "total_accepted": int(total_accepted),
            "total_pending": int(total_pending),
            "month": now.strftime("%B %Y")
        }), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_evaluation_criteria(evaluation_type):
    # البحث عن المعايير المرتبطة بنوع التقييم المحدد في قاعدة البيانات
    criteria = EvaluationCriteria.query.filter_by(evaluation_type=evaluation_type).all()
    return criteria



@app.route("/api/evaluation-stats", methods=["GET"])
def get_evaluation_stats():
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)

    # عدد التقييمات التي تحتاج مراجعة (status = "قيد المراجعة")
    need_review = Evaluation.query.filter_by(status="قيد المراجعة").count()

    # عدد التقييمات المرسلة هذا الشهر
    sent_this_month = Evaluation.query.filter(Evaluation.created_at >= start_of_month).count()

    # عدد التقييمات المقبولة هذا الشهر
    accepted_this_month = Evaluation.query.filter(
        Evaluation.status == "مقبول",
        Evaluation.created_at >= start_of_month
    ).count()

    return jsonify({
        'need_review': need_review,
        'sent_this_month': sent_this_month,
        'accepted_this_month': accepted_this_month
    })

@app.route('/get-eval', methods=['GET'])
def get_evaluations():
    evaluations = Evaluation.query.all()
    data = []
    for eval in evaluations:
        data.append({
            'id': eval.id,
            'employee_name': eval.employee_name,
            'client_name': eval.client_name,
            'service_type': eval.service_type,
            'evaluation_type': eval.evaluation_type,
            'client_consent': eval.client_consent,
            'consent_link': eval.consent_link,
            'notes': eval.notes,
            'operations_employee': eval.operations_employee,
            'operations_evaluation': eval.operations_evaluation,
            'image_path': eval.image_path,
            'status': eval.status,
            'created_at': eval.created_at.isoformat() if eval.created_at else None,
            'supervisor_note': eval.supervisor_note,
            'supervisor_name': eval.supervisor_name,
            'supervisor_action_time': eval.supervisor_action_time.isoformat() if eval.supervisor_action_time else None
        })
    return jsonify(data), 200
import cloudinary
import cloudinary.uploader
import cloudinary.api

@app.route('/delete-eval-image', methods=['POST'])
def delete_eval_image():
    data = request.get_json()
    eval_id = data.get('id')
    evaluation = db.session.get(Evaluation, eval_id)
    if evaluation and evaluation.image_path:
        # استخراج الـ public_id من المسار الذي خزنتها في قاعدة البيانات (اسم الصورة)
        public_id = evaluation.image_path.split('/')[-1].split('.')[0]  # استخراج public_id

        try:
            # حذف الصورة من Cloudinary باستخدام public_id
            cloudinary.uploader.destroy(public_id)
            
            # تحديث قاعدة البيانات لإزالة مسار الصورة
            evaluation.image_path = None
            db.session.commit()
            return jsonify({'message': 'تم حذف الصورة بنجاح '}), 200
        except Exception as e:
            return jsonify({'message': 'حدث خطأ أثناء حذف الصورة من Cloudinary', 'error': str(e)}), 500

    return jsonify({'message': 'لم يتم العثور على التقييم أو لا توجد صورة'}), 404

@app.route('/edit-eval', methods=['POST'])
def edit_evaluation():
    data = request.json
    evaluation = Evaluation.query.get(data.get('id'))
    if not evaluation:
        return jsonify({'error': 'Evaluation not found'}), 404

    # تعديل جميع الحقول المرسلة
    for key, value in data.items():
        if hasattr(evaluation, key):
            setattr(evaluation, key, value)

    db.session.commit()
    return jsonify({'message': 'تم تعديل التقييم بنجاح'}), 200

@app.route('/delete-eval', methods=['DELETE'])
def delete_evaluation():
    data = request.json
    evaluation = Evaluation.query.get(data.get('id'))
    
    if not evaluation:
        return jsonify({'error': 'Evaluation not found'}), 404

    # حذف الصورة إن وجدت من Cloudinary
    if evaluation.image_path:
        try:
            # استخراج الـ public_id من URL الصورة (إذا كنت تخزن الرابط الكامل للصورة في قاعدة البيانات)
            public_id = evaluation.image_path.split('/')[-1].split('.')[0]  # استخراج public_id من الـ URL

            # حذف الصورة من Cloudinary باستخدام الـ public_id
            cloudinary.uploader.destroy(public_id)

            # تحديث قاعدة البيانات لإزالة مسار الصورة
            evaluation.image_path = None
            db.session.commit()

        except Exception as e:
            return jsonify({'error': f'حدث خطأ أثناء حذف الصورة من Cloudinary: {str(e)}'}), 500

    # حذف التقييم من قاعدة البيانات
    db.session.delete(evaluation)
    db.session.commit()

    return jsonify({'message': 'تم حذف التقييم والصورة بنجاح'}), 200


# إضافة موظف جديد
# إضافة موظف جديد
@app.route("/api/add-employees", methods=["POST"])
def add_employee():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "لم يتم استلام بيانات"}), 400
            
        new_employee = Employee(
            name=data["name"],
            email=data["email"],
            position=data["position"],
            department=data["department"],
            password=data["password"]  # لا تشفير
        )
        db.session.add(new_employee)
        db.session.commit()
        # إعادة المعرف الجديد للموظف المضاف
        return jsonify({"message": "تمت الإضافة بنجاح", "id": new_employee.id})
    except Exception as e:
        db.session.rollback()
        print(f"خطأ في إضافة موظف: {str(e)}")
        return jsonify({"error": f"فشل الإضافة: {str(e)}"}), 500

# تعديل بيانات موظف
@app.route("/api/update-employees/<int:id>", methods=["PUT"])
def update_employee(id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "لم يتم استلام بيانات"}), 400
           
        employee = Employee.query.get(id)
        if not employee:
            return jsonify({"error": f"الموظف برقم {id} غير موجود"}), 404
           
        # تحديث البيانات
        employee.name = data.get("name", employee.name)
        employee.email = data.get("email", employee.email)
        employee.position = data.get("position", employee.position)
        employee.department = data.get("department", employee.department)
        if "password" in data and data["password"]:
            employee.password = data["password"]
       
        db.session.commit()
        return jsonify({"message": "تم التحديث بنجاح", "employee_id": id})
    except Exception as e:
        db.session.rollback()
        print(f"خطأ في التحديث: {str(e)}")
        return jsonify({"error": f"فشل التحديث: {str(e)}"}), 500

# حذف موظف
@app.route("/api/delete-employees/<int:id>", methods=["DELETE"])
def delete_employee(id):
    try:
        employee = Employee.query.get(id)
        if not employee:
            return jsonify({"error": f"الموظف برقم {id} غير موجود"}), 404
            
        db.session.delete(employee)
        db.session.commit()
        return jsonify({"message": "تم الحذف بنجاح"})
    except Exception as e:
        db.session.rollback()
        print(f"خطأ في الحذف: {str(e)}")
        return jsonify({"error": f"فشل الحذف: {str(e)}"}), 500

# جلب جميع الموظفين
@app.route("/api/get-employees", methods=["GET"])
def get_employees():
    try:
        employees = Employee.query.all()
        result = []
        for emp in employees:
            result.append({
                "id": emp.id,
                "name": emp.name,
                "email": emp.email,
                "position": emp.position,
                "department": emp.department,
                "password": emp.password
            })
        return jsonify(result)
    except Exception as e:
        print(f"خطأ في جلب الموظفين: {str(e)}")
        return jsonify({"error": f"فشل جلب البيانات: {str(e)}"}), 500

@app.route('/uploads/images/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# GET all employees
@app.route('/api/operations-employees', methods=['GET'])
def get_operations_employees():
    employees = OperationsEmployee.query.all()
    return jsonify([{'id': emp.id, 'full_name': emp.full_name, 'department': emp.department} for emp in employees])

# POST add new employee
@app.route('/api/operations-employees', methods=['POST'])
def  add_operations_employees():
    data = request.get_json()
    new_employee = OperationsEmployee(
        full_name=data['full_name'],
        department=data['department']
    )
    db.session.add(new_employee)
    db.session.commit()
    return jsonify({'message': 'Employee added successfully'}), 201

# PUT update employee
@app.route('/api/operations-employees/<int:id>', methods=['PUT'])
def update_operations_employees(id):
    data = request.get_json()
    full_name = data.get('full_name')
    department = data.get('department')

    # التحقق من وجود القيم المطلوبة
    if not full_name or not department:
        return jsonify({"error": "Full name and department are required"}), 400

    # تحديث الموظف في قاعدة البيانات
    try:
        employee = db.session.get(OperationsEmployee, id)
        if employee:
            employee.full_name = full_name
            employee.department = department
            employee.updated_at = datetime.utcnow()  # تحديث الوقت
            db.session.commit()
            return jsonify({"message": "Employee updated successfully"}), 200
        else:
            return jsonify({"error": "Employee not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# DELETE delete employee
@app.route('/api/operations-employees/<int:id>', methods=['DELETE'])
def delete_operations_employees(id):
    employee = OperationsEmployee.query.get_or_404(id)
    db.session.delete(employee)
    db.session.commit()
    return jsonify({'message': 'Employee deleted successfully'})

# إضافة معايير التقييم إلى قاعدة البيانات
@app.route('/add_criteria', methods=['POST'])
def add_criteria():
    data = request.get_json()
    evaluation_type = data.get('evaluation_type')
    value = data.get('value')

    if not evaluation_type or not value:
        return jsonify({'error': 'Invalid input'}), 400

    new_criteria = EvaluationCriteria(evaluation_type=evaluation_type, value=value)
    db.session.add(new_criteria)
    db.session.commit()

    # ✅ إرسال الكائن الجديد للفرونت إند
    return jsonify({
        'id': new_criteria.id,
        'evaluation_type': new_criteria.evaluation_type,
        'value': new_criteria.value
    }), 201

from flask import jsonify, session
from sqlalchemy.exc import SQLAlchemyError

@app.route('/api/active-evaluations', methods=['GET'])
def get_active_evaluations():
    if 'user_id' not in session:
        return jsonify({"error": "⚠️ الوصول مرفوض. يجب تسجيل الدخول أولاً."}), 401

    try:
        # استعلام التقييمات ذات الحالة "قيد المراجعة" أو "نشط"
        evaluations = Evaluation.query.filter(
            Evaluation.status.in_(['قيد المراجعة', 'نشط'])
        ).all()

        # طباعة الحالات للتأكيد
        print("🚀 Evaluation statuses:", [e.status for e in evaluations])

        if not evaluations:
             return jsonify([]), 200

        result = [
            {
                "id": e.id,
                "employee_name": e.employee_name,
                "status": e.status,
                "created_at": e.created_at.strftime('%Y-%m-%d %H:%M:%S') if e.created_at else None
            }
            for e in evaluations
        ]

        return jsonify(result), 200

    except SQLAlchemyError as e:
        return jsonify({"error": f"❌ خطأ في قاعدة البيانات: {str(e)}"}), 500


    except SQLAlchemyError as e:
        # ✅ التعامل مع أخطاء قاعدة البيانات
        return jsonify({"error": f"❌ خطأ في قاعدة البيانات: {str(e)}"}), 500

@app.route('/api/active-evaluations/<int:evaluation_id>', methods=['GET'])
def get_active_evaluation_details(evaluation_id):
    if 'user_id' not in session:
        return jsonify({"error": "غير مصرح"}), 401

    evaluation = Evaluation.query.filter(
        Evaluation.id == evaluation_id,
        Evaluation.status.in_(['قيد المراجعة', 'نشط'])
    ).first()

    if not evaluation:
        return jsonify({"error": "التقييم غير موجود أو حالته غير نشطة"}), 404

    return jsonify({
        "id": evaluation.id,
        "employee_name": evaluation.employee_name,
        "client_name": evaluation.client_name,
        "service_type": evaluation.service_type,
        "evaluation_type": evaluation.evaluation_type,
        "client_consent": evaluation.client_consent,
        "consent_link": evaluation.consent_link,
        "notes": evaluation.notes,
        "operations_employee": evaluation.operations_employee,
        "operations_evaluation": evaluation.operations_evaluation,
        "created_at": evaluation.created_at.strftime('%Y-%m-%d %H:%M:%S') if evaluation.created_at else None,
        "status": evaluation.status,
        "image_path": evaluation.image_path
    }), 200
@app.route('/api/sent-evaluations-stats', methods=['GET'])
def get_my_evaluations_stats():
    if 'user_id' not in session or 'user_name' not in session:
        return jsonify({"error": "⚠️ الوصول مرفوض. يجب تسجيل الدخول أولاً."}), 401
    
    employee_name = session['user_name']
    try:
        # حساب عدد التقييمات حسب الحالة
        total = Evaluation.query.filter(
            Evaluation.employee_name == employee_name,
            Evaluation.status.in_(['قيد المراجعة', 'نشط', 'مقبول', 'مرفوض'])
        ).count()

        accepted = Evaluation.query.filter(
            Evaluation.employee_name == employee_name,
            Evaluation.status == 'مقبول'
        ).count()

        rejected = Evaluation.query.filter(
            Evaluation.employee_name == employee_name,
            Evaluation.status == 'مرفوض'
        ).count()

        pending = Evaluation.query.filter(
            Evaluation.employee_name == employee_name,
            Evaluation.status == 'قيد المراجعة'
        ).count()

        return jsonify({
            "total": total,
            "accepted": accepted,
            "rejected": rejected,
            "pending": pending
        }), 200
    except SQLAlchemyError as e:
        return jsonify({"error": f"❌ خطأ في قاعدة البيانات: {str(e)}"}), 500
#عرض النقاط الخاصة بالموظف 
@app.route('/api/sent-evaluations', methods=['GET'])
def get_my_evaluations():
    if 'user_id' not in session or 'user_name' not in session:
        return jsonify({"error": "⚠️ الوصول مرفوض. يجب تسجيل الدخول أولاً."}), 401

    employee_name = session['user_name']

    try:
        evaluations = Evaluation.query.filter(
            Evaluation.employee_name == employee_name,
            Evaluation.status.in_(['قيد المراجعة', 'نشط', 'مقبول', 'مرفوض'])
        ).all()

        if not evaluations:
            return jsonify({"message": "لا توجد تقييمات خاصة بك حالياً."}), 200

        result = [
            {
                "id": e.id,
                "employee_name": e.employee_name,
                "status": e.status,
                "created_at": e.created_at.strftime('%Y-%m-%d %H:%M:%S') if e.created_at else None
            }
            for e in evaluations
        ]

        return jsonify(result), 200

    except SQLAlchemyError as e:
        return jsonify({"error": f"❌ خطأ في قاعدة البيانات: {str(e)}"}), 500
#2. 🧾 عرض تفاصيل تقييم معين خاص بالموظف:
@app.route('/api/sent-evaluations/<int:evaluation_id>', methods=['GET'])
def get_my_evaluation_details(evaluation_id):
    if 'user_id' not in session or 'user_name' not in session:
        return jsonify({"error": "غير مصرح"}), 401

    employee_name = session['user_name']

    evaluation = Evaluation.query.filter(
        Evaluation.id == evaluation_id,
        Evaluation.employee_name == employee_name,
        Evaluation.status.in_(['قيد المراجعة', 'نشط', 'مقبول', 'مرفوض'])
    ).first()

    if not evaluation:
        return jsonify({"error": "⚠️ التقييم غير موجود أو لا يخصك أو حالته غير مناسبة"}), 404

    return jsonify({
        "id": evaluation.id,
        "employee_name": evaluation.employee_name,
        "client_name": evaluation.client_name,
        "service_type": evaluation.service_type,
        "evaluation_type": evaluation.evaluation_type,
        "client_consent": evaluation.client_consent,
        "consent_link": evaluation.consent_link,
        "notes": evaluation.notes,
        "operations_employee": evaluation.operations_employee,
        "operations_evaluation": evaluation.operations_evaluation,
        "created_at": evaluation.created_at.strftime('%Y-%m-%d %H:%M:%S') if evaluation.created_at else None,
        "status": evaluation.status,
        "image_path": evaluation.image_path,
        "supervisor_note": evaluation.supervisor_note,
        "supervisor_name": evaluation.supervisor_name,
        "supervisor_action_time": evaluation.supervisor_action_time.strftime('%Y-%m-%d %H:%M:%S') if evaluation.supervisor_action_time else None
    }), 200


# قراءة جميع معايير التقييم من قاعدة البيانات
@app.route('/get_criteria', methods=['GET'])
def get_criteria():
    criteria_list = EvaluationCriteria.query.all()
    result = []
    for criteria in criteria_list:
        result.append({
            'id': criteria.id,
            'evaluation_type': criteria.evaluation_type,
            'value': criteria.value
        })
    return jsonify(result)

# تعديل معايير التقييم
@app.route('/update_criteria/<int:id>', methods=['PUT'])
def update_criteria(id):
    criteria = EvaluationCriteria.query.get_or_404(id)
    data = request.get_json()

    evaluation_type = data.get('evaluation_type', criteria.evaluation_type)
    value = data.get('value', criteria.value)

    criteria.evaluation_type = evaluation_type
    criteria.value = value
    db.session.commit()

    return jsonify({'message': 'Evaluation criteria updated successfully'}), 200

# حذف معايير التقييم
@app.route('/delete_criteria/<int:id>', methods=['DELETE'])
def delete_criteria(id):
    criteria = EvaluationCriteria.query.get_or_404(id)
    db.session.delete(criteria)
    db.session.commit()

    return jsonify({'message': 'Evaluation criteria deleted successfully'}), 200

@app.route('/operations_employees', methods=['GET'])
def get_operations_employee():
    # جلب جميع الموظفين
    employees = OperationsEmployee.query.all()
    
    # تسلسل البيانات لتضمين فقط الاسم
    employees_list = [
        {
            'full_name': employee.full_name
        } for employee in employees
    ]
    
    return jsonify(employees_list)


# نقطة الدخول لتسجيل الدخول
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # تحقق من صحة بيانات الدخول
    employee = Employee.query.filter_by(email=email).first()
    if employee and employee.password == password:  # تحذير: ينصح باستخدام bcrypt في الواقع العملي
        session.permanent = True
        session['user_id'] = employee.id
        session['user_email'] = employee.email
        session['user_name'] = employee.name
        session['user_role'] = employee.position
        session.modified = True
        print(f"Session Data: {session}")


        return jsonify({
            "message": "تم تسجيل الدخول بنجاح",
            "user": {
                "id": employee.id,
                "name": employee.name,
                "email": employee.email,
                "position": employee.position,
                "department": employee.department
            }
        }), 200
    else:
        return jsonify({"message": "البريد الإلكتروني أو كلمة المرور غير صحيحة"}), 401

# نقطة الوصول لعرض جميع الموظفين
@app.route('/api/employees', methods=['GET'])
def get_all_employees():
    try:
        employees = Employee.query.with_entities(Employee.name).all()
        names = [emp.name for emp in employees]
        return jsonify(names), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# راوت خاص بالموظف: جلب فقط أسماء أنواع التقييم
@app.route('/evaluation_criteria', methods=['GET'])
def get_evaluation_types():
    criteria = EvaluationCriteria.query.with_entities(EvaluationCriteria.evaluation_type).distinct().all()
    evaluation_types = [c.evaluation_type for c in criteria]
    return jsonify(evaluation_types)

# نقطة الوصول لعرض بيانات المستخدم الحالي
@app.route('/current-user', methods=['GET'])
def current_user():
    if 'user_id' not in session:
        return jsonify({"message": "غير مصرح بالوصول"}), 401
    
    employee = Employee.query.get(session['user_id'])
    
    if not employee:
        return jsonify({"message": "المستخدم غير موجود"}), 404
        
    return jsonify({
        "id": employee.id,
        "name": employee.name,
        "email": employee.email,
        "position": employee.position,
        "department": employee.department
    }), 200

# نقطة الوصول لعرض بيانات الملف الشخصي
@app.route('/profile', methods=['GET'])
def profile():
    print("Session data:", dict(session))  # طباعة مفصلة لمحتوى الجلسة
    print("User email in session:", session.get('user_email'))
    
    if 'user_email' in session:
        return jsonify({
            'full_name': session['user_name'],
            'email': session['user_email']
        }), 200
    else:
        return jsonify({
            'message': 'لم يتم تسجيل الدخول',
            'session_data': dict(session)  # إرجاع بيانات الجلسة للتصحيح
        }), 401

from datetime import datetime
import os

@app.route('/submit_evaluation', methods=['POST'])
def submit_evaluation():
    try:
        # استخراج البيانات من الـ FormData
        employee_name = request.form.get('employeeName')
        client_name = request.form.get('clientName')
        service_type = request.form.get('serviceType')
        evaluation_type = request.form.get('evaluationType')

        # التحقق من الحقول الأساسية
        if not service_type:
            return jsonify({"error": "service_type is required and cannot be empty"}), 400
        if not employee_name or not client_name:
            return jsonify({"error": "employee_name and client_name are required"}), 400

        client_consent = request.form.get('clientConsent', "لا")
        consent_link = request.form.get('consentLink', "")
        notes = request.form.get('notes', "")
        operations_employee = request.form.get('operationsEmployee')
        operations_evaluation = request.form.get('operationsEvaluation')
        local_device_time = request.form.get('localDeviceTime')

        print(f"Received local_device_time: {local_device_time}")
        print(f"Received form data: {request.form}")

        # محاولة تحويل local_device_time إلى datetime
        try:
            local_device_time = datetime.strptime(local_device_time, "%m/%d/%Y, %I:%M:%S %p")
            print(f"Received local_device_time: {local_device_time}")
        except ValueError:
            return jsonify({"error": "Invalid date format. Expected format: YYYY-MM-DD HH:MM:SS"}), 400

        # تحويل client_consent من "نعم" و "لا" إلى True و False
        if client_consent == "نعم":
            client_consent = True
        else:
            client_consent = False

        # إذا كانت موافقة العميل "لا"، يجب أن يكون رابط الموافقة فارغًا
        if client_consent == False:
            consent_link = None


        # التعامل مع الصورة (إذا كانت موجودة)
        image = request.files.get('image')
        image_path = None
        if image:
            # استخراج الامتداد وتوليد اسم فريد باستخدام uuid
            ext = image.filename.split('.')[-1]  # استخراج الامتداد مثل jpg, png
            unique_filename = f"{uuid.uuid4().hex}.{ext}"

            # رفع الصورة إلى Cloudinary باستخدام الاسم الفريد
            upload_result = cloudinary.uploader.upload(image, public_id=unique_filename)
            image_path = upload_result['secure_url']  # الحصول على الرابط الآمن للصورة

        # تخزين البيانات في قاعدة البيانات
        evaluation = Evaluation(
            employee_name=employee_name,
            client_name=client_name,
            service_type=service_type,
            evaluation_type=evaluation_type,
            client_consent=client_consent,
            consent_link=consent_link,
            notes=notes,
            operations_employee=operations_employee,
            operations_evaluation=operations_evaluation,
            image_path=image_path,
            created_at=local_device_time,
            status='قيد المراجعة',
            supervisor_note="",
            supervisor_name=None,
            supervisor_action_time=None
        )

        db.session.add(evaluation)
        db.session.commit()

        return jsonify({"message": "Evaluation submitted successfully!"}), 200
    except Exception as e:
        print(f"Error occurred: {str(e)}")  # سيتم طباعة تفاصيل الخطأ
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/update-evaluation-status/<int:id>', methods=['PUT'])
def update_evaluation_status(id):
    try:
        if 'user_id' not in session:
            return jsonify({"message": "يجب تسجيل الدخول أولاً"}), 401

        data = request.get_json()
        status = data.get('status')
        supervisor_note = data.get('supervisor_note', '')
        supervisor_name = data.get('supervisor_name', '')
        timestamp = data.get('timestamp')  # استلام الوقت المحلي من العميل
        print(f"الوقت المستلم من العميل: {timestamp}")  # طباعة الوقت المستلم للاختبار

        if status not in ['مقبول', 'مرفوض']:
            return jsonify({"message": "حالة غير صالحة. يجب أن تكون 'مقبول' أو 'مرفوض'"}), 400

        evaluation = db.session.get(Evaluation, id)
        if not evaluation:
            return jsonify({"message": "التقييم غير موجود"}), 404

        # تحديث الحقول
        evaluation.status = status
        evaluation.supervisor_note = supervisor_note
        evaluation.supervisor_name = supervisor_name

        # استخدام الوقت المحلي الذي أرسله العميل بدلاً من الوقت الحالي
        if timestamp:
            evaluation.supervisor_action_time = parse_timestamp(timestamp)  # معالجة الوقت هنا
        else:
            evaluation.supervisor_action_time = datetime.utcnow()  # إذا لم يكن هناك وقت مرسل، استخدم الوقت الحالي UTC

        # إذا كانت الحالة "مقبول"، حساب النقاط بناءً على نوع التقييم
        if status == "مقبول":
            # استرجاع المعايير التي تتعلق بهذا النوع من التقييم
            criteria = get_evaluation_criteria(evaluation.evaluation_type)
            total_points = sum([criterion.value for criterion in criteria])  # حساب مجموع النقاط بناءً على المعايير

            # تحديث النقاط للتقييم
            evaluation.points = total_points

            # تحديث النقاط الإجمالية للموظف
            employee = Employee.query.filter_by(name=evaluation.employee_name).first()
            if employee:
                employee.points += total_points  # إضافة النقاط للتقييم إلى النقاط الإجمالية
        create_notification_for_employee(evaluation, status)
        db.session.commit()
        return jsonify({
            "message": "تم تحديث التقييم بنجاح",
            "data": {
                "id": evaluation.id,
                "status": evaluation.status,
                "supervisor_name": evaluation.supervisor_name,
                "updated_at": evaluation.supervisor_action_time.isoformat(),
                "points": evaluation.points  # إضافة النقاط المحدثة في الاستجابة
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating evaluation: {str(e)}")
        return jsonify({
            "message": "حدث خطأ أثناء تحديث التقييم",
            "error": str(e)
        }), 500

# نقطة الخروج من الجلسة (تسجيل الخروج)
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # مسح جميع بيانات الجلسة
    return jsonify({"message": "تم تسجيل الخروج بنجاح"}), 200

# نقطة الدخول الرئيسية للتطبيق
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
