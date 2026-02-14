from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os
import io
import csv
import json
import traceback
from sqlalchemy import or_, func, desc, asc
from flask_mail import Mail, Message
import random

from config import config
# FIXED: Added Notification to imports
from models import (
    db, User, Organization, Barangay, AgriculturalProduct, Farmer, 
    FarmerProduct, FarmerChild, FarmerExperience, ResearchProject,
    SurveyQuestionnaire, ActivityLog, Notification
)

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Define allowed extensions for image upload
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    # Ensure UPLOAD_FOLDER is set
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

    # Initialize extensions (SQLAlchemy)
    db.init_app(app)
    
    # Allow specific origin for CORS - Enhanced headers
    CORS(app, 
     resources={r"/api/*": {"origins": ["http://localhost:3000", "https://agridata.ct.ws"]}}, 
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

    jwt = JWTManager(app)
    
    # Add this specific handler for Preflight (OPTIONS) requests
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            res = jsonify({'status': 'ok'})
            res.headers.add("Access-Control-Allow-Origin", request.headers.get("Origin"))
            res.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
            res.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
            return res, 200
    
    # Create upload folder immediately
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        print(f"📁 Verified Upload folder at: {app.config['UPLOAD_FOLDER']}")
    except Exception as e:
        print(f"❌ Error creating upload folder: {e}")
    
    # --- HELPER FUNCTIONS ---

    def log_activity(action, entity_type=None, entity_id=None, details=None):
        try:
            user_id = get_jwt_identity()
            # Handle case where activity is logged during login/public events where token might be missing
            if not user_id:
                return 

            str_entity_id = str(entity_id) if entity_id else None
            
            log = ActivityLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=str_entity_id,
                details=details,
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            print(f"Logging error: {e}")
            db.session.rollback()
            pass

    # ADDED: Notification Helper
    def broadcast_notification(title, message, target_user_id=None):
        """
        Creates a notification record.
        target_user_id: None for System-Wide, or ID for specific user.
        """
        try:
            new_alert = Notification(
                user_id=target_user_id, 
                title=title,
                message=message,
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.session.add(new_alert)
            # Note: We let the calling function do the commit to ensure transaction integrity
        except Exception as e:
            print(f"Notification Creation Error: {str(e)}")
    
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    def save_profile_image(file):
        if file and file.filename:
            if allowed_file(file.filename):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                original_filename = secure_filename(file.filename)
                filename = f"{timestamp}_{original_filename}"
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(filepath)
                    print(f"✅ Image saved: {filename} at {filepath}")
                    return filename
                except Exception as e:
                    print(f"❌ Error saving file: {e}")
                    return None
            else:
                print(f"❌ Invalid file type: {file.filename}")
        else:
            print("❌ No file or filename provided")
        return None
    
    def delete_profile_image(filename):
        if filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    print(f"🗑️ Deleted old image: {filename}")
                    return True
                except Exception as e:
                    print(f"Error deleting file {filename}: {e}")
        return False
    
    # ============ Static File Serving (Images) ============
    @app.route('/static/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # ============ Authentication Routes ============
    
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        try:
            data = request.get_json()
            
            if User.query.filter_by(username=data['username']).first():
                return jsonify({'error': 'Username already exists'}), 400
            
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email already exists'}), 400
            
            user = User(
                username=data['username'],
                email=data['email'],
                full_name=data['full_name'],
                role=data.get('role', 'viewer'),
                organization_id=data.get('organization') 
            )
            user.set_password(data['password'])
            
            db.session.add(user)
            db.session.commit()
            
            return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = request.get_json()
        
        user = User.query.filter_by(username=data['username']).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 403
        
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }), 200
    
    @app.route('/api/auth/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh():
        user_id = get_jwt_identity()
        access_token = create_access_token(identity=user_id)
        return jsonify({'access_token': access_token}), 200
    
    @app.route('/api/auth/me', methods=['GET'])
    @jwt_required()
    def get_current_user():
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify(user.to_dict()), 200
    
    
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'markronald265@gmail.com'
    app.config['MAIL_PASSWORD'] = 'qlfxiqvfyodybpsz'
    app.config['MAIL_DEFAULT_SENDER'] = 'markronald265@gmail.com'
    mail = Mail(app)

    otp_storage = {} 
    
    @app.route('/api/auth/forgot-password', methods=['POST'])
    def request_otp():
        email = request.json.get('email')
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"error": "This email is not registered in our system handle."}), 404
        
        otp = str(random.randint(100000, 999999))
        otp_storage[email] = {"otp": otp, "timestamp": datetime.now()}
        
        try:
            msg = Message(
                subject="AgriData | Identity Verification Code",
                recipients=[email]
            )
            
            msg.body = f"Identity recovery initiated. Your 6-digit verification code is: {otp}"
            
            msg.html = f"""
            <div style="font-family: 'Inter', sans-serif; background-color: #f8fafc; padding: 40px; color: #0f172a;">
                <div style="max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 24px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
                    <div style="background: #041d18; padding: 30px; text-align: center;">
                        <h1 style="color: #10b981; margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 2px; font-weight: 900;">AgriData</h1>
                        <p style="color: #4ade80; margin: 5px 0 0 0; font-size: 10px; text-transform: uppercase; letter-spacing: 3px;">Systems Hub</p>
                    </div>
                    <div style="padding: 40px; text-align: center;">
                        <h2 style="font-size: 20px; font-weight: 800; color: #1e293b; margin-bottom: 8px; text-transform: uppercase;">Identity Verification</h2>
                        <p style="color: #64748b; font-size: 14px; margin-bottom: 30px;">A password reset request was initiated for your account. Use the secure code below to proceed.</p>
                        
                        <div style="background: #f1f5f9; padding: 20px; border-radius: 16px; border: 1px dashed #cbd5e1; margin-bottom: 30px;">
                            <span style="font-family: monospace; font-size: 36px; font-weight: 900; letter-spacing: 8px; color: #041d18;">{otp}</span>
                        </div>
                        
                        <p style="color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Expires in 10 minutes</p>
                    </div>
                    <div style="background: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #f1f5f9;">
                        <p style="color: #94a3b8; font-size: 10px; margin: 0;">If you did not request this, please ignore this email or contact system governance.</p>
                    </div>
                </div>
                <p style="text-align: center; color: #cbd5e1; font-size: 10px; margin-top: 20px; text-transform: uppercase; letter-spacing: 1px;">© 2026 Institutional Registry • Secure Automated System</p>
            </div>
            """
            
            mail.send(msg)
            return jsonify({"message": "OTP sent to your Gmail."}), 200
            
        except Exception as e:
            print(f"SMTP ERROR: {str(e)}") 
            return jsonify({"error": "Mail delivery failure. Ensure App Password is valid."}), 500
        
    @app.route('/api/auth/reset-password', methods=['POST'])
    def reset_password():
        data = request.get_json()
        email = data.get('email')
        otp_received = data.get('otp')
        new_password = data.get('new_password')

        if email in otp_storage and otp_storage[email]['otp'] == otp_received:
            user = User.query.filter_by(email=email).first()
            if user:
                user.set_password(new_password)
                db.session.commit()
                del otp_storage[email]
                return jsonify({"message": "Password updated successfully."}), 200
        
        return jsonify({"error": "Invalid or expired verification code."}), 400
    
    @app.route('/api/auth/verify-otp', methods=['POST'])
    def verify_otp():
        data = request.get_json()
        email = data.get('email')
        otp_received = data.get('otp')

        if email in otp_storage:
            stored_otp_data = otp_storage[email]
            if stored_otp_data['otp'] == str(otp_received):
                return jsonify({"message": "Identity verified successfully."}), 200
            else:
                return jsonify({"error": "Invalid verification code. Please check your Gmail."}), 400
        
        return jsonify({"error": "Session expired. Please request a new code."}), 404

    # ============ Dashboard Routes ============
    
    @app.route('/api/dashboard/stats', methods=['GET'])
    @jwt_required()
    def get_dashboard_stats():
        total_farmers = Farmer.query.count()
        total_barangays = Barangay.query.count()
        total_products = AgriculturalProduct.query.count()
        total_experiences = FarmerExperience.query.count()
        total_projects = ResearchProject.query.count()
        
        children_farming = FarmerChild.query.filter_by(continues_farming=True).count()
        total_children = FarmerChild.query.count()
        
        recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
        
        education_stats_query = db.session.query(
            Farmer.education_level, func.count(Farmer.id)
        ).group_by(Farmer.education_level).all()
        
        education_stats = [{'level': level, 'count': count} for level, count in education_stats_query]
        
        product_stats_query = db.session.query(
            Barangay.name, func.count(Farmer.id)
        ).join(Farmer.barangay).group_by(Barangay.name).order_by(func.count(Farmer.id).desc()).limit(5).all()
        
        product_stats = [{'barangay': name, 'count': count} for name, count in product_stats_query]
        
        return jsonify({
            'total_farmers': total_farmers,
            'total_barangays': total_barangays,
            'total_products': total_products,
            'total_experiences': total_experiences,
            'total_projects': total_projects,
            'children_farming': children_farming,
            'total_children': total_children,
            'recent_activities': [log.to_dict() for log in recent_activities],
            'education_stats': education_stats,
            'product_stats': product_stats
        }), 200
    
    # ============ Notification Routes (FIXED) ============
    
    @app.route('/api/notifications', methods=['GET'])
    @jwt_required()
    def get_notifications():
        try:
            current_user_id = get_jwt_identity()
            
            # Fetch User-Specific AND System-Wide notifications
            notifications = Notification.query.filter(
                (Notification.user_id == current_user_id) | (Notification.user_id == None)
            ).order_by(Notification.created_at.desc()).limit(20).all()
            
            return jsonify([n.to_dict() for n in notifications]), 200
        except Exception as e:
            print(f"Notification Error: {e}")
            return jsonify([]), 200

    @app.route('/api/notifications/<int:id>/read', methods=['PUT'])
    @jwt_required()
    def mark_read(id):
        try:
            # We don't filter by user_id here because we might be marking a System Msg (NULL) as read
            notif = Notification.query.get_or_404(id)
            notif.is_read = True
            db.session.commit()
            return jsonify({"message": "Read status updated"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/api/notifications/read-all', methods=['PUT'])
    @jwt_required()
    def mark_all_notifications_read():
        try:
            current_user_id = get_jwt_identity()
            
            # FIX: Update BOTH personal AND system-wide notifications
            Notification.query.filter(
                or_(Notification.user_id == current_user_id, Notification.user_id == None),
                Notification.is_read == False
            ).update({Notification.is_read: True}, synchronize_session=False)
            
            db.session.commit()
            return jsonify({"message": "All marked as read"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/api/notifications', methods=['DELETE'])
    @jwt_required()
    def clear_notifications():
        try:
            current_user_id = get_jwt_identity()
            
            # FIX: Delete BOTH personal AND system-wide notifications
            # WARNING: This deletes system messages for EVERYONE. 
            # In a real app, you would 'hide' them, but for this prototype, this fixes the "coming back" bug.
            Notification.query.filter(
                (Notification.user_id == current_user_id) | (Notification.user_id == None)
            ).delete(synchronize_session=False)
            
            db.session.commit()
            return jsonify({"message": "Registry cleared"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    # ============ Farmer Routes ============

    @app.route('/api/farmers', methods=['GET'])
    @jwt_required()
    def get_farmers():
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', app.config.get('ITEMS_PER_PAGE', 20), type=int)
        search = request.args.get('search', '')
        barangay_id = request.args.get('barangay_id')
        
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        query = Farmer.query
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Farmer.first_name.ilike(search_term),
                    Farmer.last_name.ilike(search_term),
                    Farmer.farmer_code.ilike(search_term)
                )
            )
        
        if barangay_id:
            query = query.filter(Farmer.barangay_id == barangay_id)
        
        if hasattr(Farmer, sort_by):
            col = getattr(Farmer, sort_by)
            if sort_order == 'asc':
                query = query.order_by(col.asc())
            else:
                query = query.order_by(col.desc())
        else:
            query = query.order_by(Farmer.created_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'farmers': [farmer.to_dict(include_relations=True) for farmer in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }), 200
    
    @app.route('/api/farmers/<int:id>', methods=['GET'])
    @jwt_required()
    def get_farmer(id):
        farmer = Farmer.query.get_or_404(id)
        
        products = FarmerProduct.query.filter_by(farmer_id=id).all()
        children = FarmerChild.query.filter_by(farmer_id=id).all()
        experiences = FarmerExperience.query.filter_by(farmer_id=id).all()
        
        data = farmer.to_dict(include_relations=True)
        data['products'] = [p.to_dict() for p in products]
        data['children'] = [c.to_dict() for c in children]
        data['experiences'] = [e.to_dict() for e in experiences]
        
        return jsonify(data), 200
    
    @app.route('/api/farmers', methods=['POST'])
    @jwt_required()
    def create_farmer():
        current_user = User.query.get(get_jwt_identity())
        if current_user.role not in ['admin', 'researcher', 'data_encoder']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        try:
            data = request.form.to_dict()
            
            def get_val(key, type_cast=None, default=None):
                val = data.get(key)
                if val in ['', 'null', 'undefined', None]: return default
                if type_cast:
                    try: return type_cast(val)
                    except: return default
                return val

            profile_image = save_profile_image(request.files['profile_image']) if 'profile_image' in request.files else None
            
            birth_date_val = None
            age_val = get_val('age', int)

            if data.get('birth_date'):
                try:
                    birth_date_val = datetime.strptime(data['birth_date'][:10], '%Y-%m-%d').date()
                    if age_val is None:
                        today = date.today()
                        age_val = today.year - birth_date_val.year - ((today.month, today.day) < (birth_date_val.month, birth_date_val.day))
                except (ValueError, TypeError):
                    pass

            if age_val is None:
                age_val = 0

            farmer = Farmer(
                farmer_code=data.get('farmer_code'), first_name=data.get('first_name'), middle_name=get_val('middle_name'),
                last_name=data.get('last_name'), suffix=get_val('suffix'), 
                age=age_val, 
                gender=data.get('gender', 'Male'),
                profile_image=profile_image, birth_date=birth_date_val, barangay_id=get_val('barangay_id', int),
                organization_id=get_val('organization_id', int), data_encoder_id=current_user.id, address=data.get('address'),
                contact_number=data.get('contact_number'), education_level=data.get('education_level', 'Elementary'),
                annual_income=get_val('annual_income', float), income_source=data.get('income_source'),
                number_of_children=get_val('number_of_children', int, 0),
                children_farming_involvement=data.get('children_farming_involvement') in ['true', True, '1'],
                primary_occupation=data.get('primary_occupation'), secondary_occupation=data.get('secondary_occupation'),
                farm_size_hectares=get_val('farm_size_hectares', float, 0), land_ownership=data.get('land_ownership', 'Owner'),
                years_farming=get_val('years_farming', int)
            )
            db.session.add(farmer)
            
            # --- AUTO-NOTIFICATION TRIGGER ---
            broadcast_notification(
                title="New Farmer Onboarded", 
                message=f"{data.get('first_name')} {data.get('last_name')} has been registered by {current_user.full_name}.",
                target_user_id=None # Broadcast to all
            )
            # ---------------------------------

            db.session.commit()

            if data.get('products'):
                try:
                    for p in json.loads(data['products']):
                        if not p.get('product_name'): continue
                        prod = AgriculturalProduct.query.filter(func.lower(AgriculturalProduct.name) == func.lower(p['product_name'].strip())).first()
                        if not prod:
                            prod = AgriculturalProduct(name=p['product_name'].strip(), category='Crop')
                            db.session.add(prod)
                            db.session.commit()
                        db.session.add(FarmerProduct(farmer_id=farmer.id, product_id=prod.id, production_volume=p.get('production_volume', 0), unit=p.get('unit', 'kg'), is_primary=p.get('is_primary', False)))
                    db.session.commit()
                except: pass

            log_activity('FARMER_CREATED', 'Farmer', farmer.id, f"Created: {farmer.first_name} {farmer.last_name}")
            return jsonify({'message': 'Success', 'farmer': farmer.to_dict()}), 201
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: {e}")
            return jsonify({'error': str(e)}), 400
        
    @app.route('/api/organizations', methods=['POST'])
    @jwt_required()
    def create_organization():
        if User.query.get(get_jwt_identity()).role != 'admin': return jsonify({'error': 'Unauthorized'}), 403
        data = request.get_json()
        try:
            org = Organization(
                name=data['name'],
                type=data.get('type', 'Cooperative'),
                description=data.get('description'),
            )
            db.session.add(org)
            db.session.commit()
            return jsonify({'message': 'Success', 'organization': org.to_dict()}), 201
        except Exception as e: return jsonify({'error': str(e)}), 400

    @app.route('/api/organizations/<int:id>', methods=['PUT'])
    @jwt_required()
    def update_organization(id):
        if User.query.get(get_jwt_identity()).role != 'admin': return jsonify({'error': 'Unauthorized'}), 403
        org = Organization.query.get_or_404(id)
        data = request.get_json()
        try:
            for k, v in data.items():
                if hasattr(org, k) and k != 'id': setattr(org, k, v)
            db.session.commit()
            return jsonify({'message': 'Updated', 'organization': org.to_dict()}), 200
        except Exception as e: return jsonify({'error': str(e)}), 400

    @app.route('/api/organizations/<int:id>', methods=['DELETE'])
    @jwt_required()
    def delete_organization(id):
        if User.query.get(get_jwt_identity()).role != 'admin': return jsonify({'error': 'Unauthorized'}), 403
        try:
            db.session.delete(Organization.query.get_or_404(id))
            db.session.commit()
            return jsonify({'message': 'Deleted'}), 200
        except: return jsonify({'error': 'Cannot delete active organization'}), 400
    
    @app.route('/api/farmers/<int:id>', methods=['PUT'])
    @jwt_required()
    def update_farmer(id):
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin', 'researcher', 'data_encoder']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        farmer = Farmer.query.get_or_404(id)
        
        try:
            data = request.form.to_dict()

            if 'profile_image' in request.files:
                file = request.files['profile_image']
                new_filename = save_profile_image(file)
                if new_filename:
                    if farmer.profile_image:
                        delete_profile_image(farmer.profile_image)
                    farmer.profile_image = new_filename

            excluded_keys = [
                'id', 'created_at', 'updated_at', 'data_encoder_id', 'profile_image', 
                'products', 'children', 'experiences', 
                'barangay', 'organization', 'data_encoder',
                'full_name'
            ]

            for key, value in data.items():
                if hasattr(farmer, key) and key not in excluded_keys:
                    if key == 'birth_date':
                        if value and value != 'null' and value != '':
                            try:
                                farmer.birth_date = datetime.strptime(value[:10], '%Y-%m-%d').date()
                            except (ValueError, TypeError):
                                pass 
                        else:
                            farmer.birth_date = None
                            
                    elif key in ['barangay_id', 'organization_id', 'years_farming', 'number_of_children', 'age']:
                        if value and value != 'null' and value != '':
                            try:
                                setattr(farmer, key, int(value))
                            except (ValueError, TypeError):
                                pass
                        else:
                            if key not in ['barangay_id', 'age'] or value == '': 
                                setattr(farmer, key, None)
                    
                    elif key in ['farm_size_hectares', 'annual_income']:
                        if value and value != 'null' and value != '':
                            try:
                                setattr(farmer, key, float(value))
                            except (ValueError, TypeError):
                                pass
                        else:
                            setattr(farmer, key, None)
                            
                    elif key == 'children_farming_involvement':
                        farmer.children_farming_involvement = value in ['true', True, 1, '1']
                    
                    else:
                        setattr(farmer, key, value)

            products_json = data.get('products')
            if products_json:
                try:
                    FarmerProduct.query.filter_by(farmer_id=farmer.id).delete()
                    products_list = json.loads(products_json)
                    for prod_data in products_list:
                        if not prod_data.get('product_name'):
                            continue

                        prod_name = prod_data['product_name'].strip()
                        agri_product = AgriculturalProduct.query.filter(
                            func.lower(AgriculturalProduct.name) == func.lower(prod_name)
                        ).first()

                        if not agri_product:
                            agri_product = AgriculturalProduct(name=prod_name, category='Crop')
                            db.session.add(agri_product)
                            db.session.commit()

                        farmer_product = FarmerProduct(
                            farmer_id=farmer.id,
                            product_id=agri_product.id,
                            production_volume=prod_data.get('production_volume', 0),
                            unit=prod_data.get('unit', 'kg'),
                            is_primary=prod_data.get('is_primary', False)
                        )
                        db.session.add(farmer_product)
                        
                except json.JSONDecodeError:
                    print("Error decoding products JSON during update")
            
            db.session.commit()
            
            log_activity('FARMER_UPDATED', 'Farmer', farmer.id, f"Updated farmer: {farmer.first_name} {farmer.last_name}")
            
            return jsonify({'message': 'Farmer updated successfully', 'farmer': farmer.to_dict()}), 200
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ UPDATE ERROR: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Failed to update record: {str(e)}'}), 400
    
    @app.route('/api/farmers/<int:id>', methods=['DELETE'])
    @jwt_required()
    def delete_farmer(id):
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        farmer = Farmer.query.get_or_404(id)
        
        FarmerProduct.query.filter_by(farmer_id=id).delete()
        FarmerChild.query.filter_by(farmer_id=id).delete()
        FarmerExperience.query.filter_by(farmer_id=id).delete()
        
        if farmer.profile_image:
            delete_profile_image(farmer.profile_image)
        
        log_activity('FARMER_DELETED', 'Farmer', farmer.id, f"Deleted farmer: {farmer.first_name} {farmer.last_name}")
        
        db.session.delete(farmer)
        db.session.commit()
        
        return jsonify({'message': 'Farmer deleted successfully'}), 200
    
    # ============ Survey Questionnaires Routes ============
    
    @app.route('/api/surveys', methods=['GET'])
    @jwt_required()
    def get_surveys():
        surveys = SurveyQuestionnaire.query.order_by(SurveyQuestionnaire.created_at.desc()).all()
        return jsonify([s.to_dict() for s in surveys]), 200
    
    @app.route('/api/surveys', methods=['POST'])
    @jwt_required()
    def create_survey():
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin', 'researcher']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        try:
            survey = SurveyQuestionnaire(
                title=data['title'],
                description=data.get('description'),
                category=data.get('category', 'General'),
                is_active=data.get('is_active', True),
                created_by_id=current_user.id
            )
            db.session.add(survey)
            db.session.commit()
            
            log_activity('SURVEY_CREATED', 'SurveyQuestionnaire', survey.id, f"Created survey: {survey.title}")
            return jsonify({'message': 'Survey created successfully', 'survey': survey.to_dict()}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    @app.route('/api/surveys/<int:id>', methods=['PUT'])
    @jwt_required()
    def update_survey(id):
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin', 'researcher']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        survey = SurveyQuestionnaire.query.get_or_404(id)
        data = request.get_json()
        
        try:
            for key, value in data.items():
                if hasattr(survey, key) and key not in ['id', 'created_at', 'created_by_id']:
                    setattr(survey, key, value)
            
            db.session.commit()
            return jsonify({'message': 'Survey updated', 'survey': survey.to_dict()}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    @app.route('/api/surveys/<int:id>', methods=['DELETE'])
    @jwt_required()
    def delete_survey(id):
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        try:
            survey = SurveyQuestionnaire.query.get_or_404(id)
            db.session.delete(survey)
            db.session.commit()
            return jsonify({'message': 'Survey deleted'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Cannot delete survey (may have responses)'}), 400
    
    # ============ Farmer Products Routes (Standalone) ============
    
    @app.route('/api/farmers/<int:farmer_id>/products', methods=['POST'])
    @jwt_required()
    def add_farmer_product(farmer_id):
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin', 'researcher', 'data_encoder']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        product = FarmerProduct(
            farmer_id=farmer_id,
            product_id=data['product_id'],
            production_volume=data.get('production_volume'),
            unit=data.get('unit'),
            is_primary=data.get('is_primary', False),
            selling_price=data.get('selling_price')
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify({'message': 'Product added successfully', 'product': product.to_dict()}), 201
    
    # ============ Farmer Children Routes ============
    
    @app.route('/api/farmers/<int:farmer_id>/children', methods=['POST'])
    @jwt_required()
    def add_farmer_child(farmer_id):
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin', 'researcher', 'data_encoder']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        child = FarmerChild(
            farmer_id=farmer_id,
            name=data.get('name'),
            age=data.get('age'),
            gender=data.get('gender'),
            education_level=data.get('education_level'),
            continues_farming=data.get('continues_farming', False),
            involvement_level=data.get('involvement_level', 'None'),
            current_occupation=data.get('current_occupation'),
            notes=data.get('notes')
        )
        
        db.session.add(child)
        db.session.commit()
        
        return jsonify({'message': 'Child record added successfully', 'child': child.to_dict()}), 201
    
    # ============ Farmer Experiences Routes ============
    
    @app.route('/api/experiences', methods=['GET'])
    @jwt_required()
    def get_experiences():
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', app.config.get('ITEMS_PER_PAGE', 20), type=int)
        
        pagination = FarmerExperience.query.order_by(FarmerExperience.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'experiences': [exp.to_dict(include_relations=True) for exp in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }), 200
    
    @app.route('/api/experiences', methods=['POST'])
    @jwt_required()
    def create_experience():
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin', 'researcher', 'data_encoder']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        experience = FarmerExperience(
            farmer_id=data['farmer_id'],
            experience_type=data['experience_type'],
            title=data['title'],
            description=data['description'],
            date_recorded=datetime.strptime(data['date_recorded'], '%Y-%m-%d').date() if data.get('date_recorded') else date.today(),
            interviewer_id=current_user.id,
            location=data.get('location'),
            context=data.get('context'),
            impact_level=data.get('impact_level')
        )
        
        db.session.add(experience)
        
        # --- AUTO-NOTIFICATION TRIGGER ---
        broadcast_notification(
            title="Knowledge Base Update", 
            message=f"New {data['experience_type']} recorded: '{data['title']}'",
            target_user_id=None
        )
        # ---------------------------------

        db.session.commit()
        
        log_activity('EXPERIENCE_CREATED', 'FarmerExperience', experience.id)
        
        return jsonify({'message': 'Experience recorded successfully', 'experience': experience.to_dict()}), 201
    
    # ============ Research Projects Routes ============
    
    @app.route('/api/projects', methods=['GET'])
    @jwt_required()
    def get_projects():
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', app.config.get('ITEMS_PER_PAGE', 20), type=int)
        
        pagination = ResearchProject.query.order_by(ResearchProject.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'projects': [proj.to_dict(include_relations=True) for proj in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }), 200
    
    @app.route('/api/projects', methods=['POST'])
    @jwt_required()
    def create_project():
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin', 'researcher']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        project = ResearchProject(
            project_code=data.get('project_code'),
            title=data['title'],
            description=data.get('description'),
            principal_investigator_id=current_user.id,
            organization_id=data.get('organization_id'),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else None,
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
            status=data.get('status', 'Planning'),
            research_type=data['research_type'],
            objectives=data.get('objectives'),
            methodology=data.get('methodology'),
            budget=data.get('budget'),
            funding_source=data.get('funding_source')
        )
        
        db.session.add(project)
        
        # --- AUTO-NOTIFICATION TRIGGER ---
        broadcast_notification(
            title="Research Initiative Launched", 
            message=f"Project '{data['title']}' has been initiated by {current_user.full_name}.",
            target_user_id=None
        )
        # ---------------------------------

        db.session.commit()
        
        log_activity('PROJECT_CREATED', 'ResearchProject', project.id, f"Created project: {project.title}")
        
        return jsonify({'message': 'Project created successfully', 'project': project.to_dict()}), 201
    
    # ============ Barangay Routes ============
    
    @app.route('/api/barangays', methods=['GET'])
    @jwt_required()
    def get_barangays():
        barangays = Barangay.query.order_by(Barangay.name).all()
        return jsonify([b.to_dict() for b in barangays]), 200
    
    @app.route('/api/barangays', methods=['POST'])
    @jwt_required()
    def create_barangay():
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin', 'data_encoder']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        barangay = Barangay(
            name=data['name'],
            municipality=data['municipality'],
            province=data['province'],
            region=data['region'],
            population=data.get('population'),
            total_households=data.get('total_households'),
            agricultural_households=data.get('agricultural_households')
        )
        
        db.session.add(barangay)
        db.session.commit()
        
        return jsonify({'message': 'Barangay created successfully', 'barangay': barangay.to_dict()}), 201
    
    # ============ Products Routes ============
    
    @app.route('/api/products', methods=['GET'])
    @jwt_required()
    def get_products():
        products = AgriculturalProduct.query.order_by(AgriculturalProduct.name).all()
        return jsonify([p.to_dict() for p in products]), 200
    
    @app.route('/api/products', methods=['POST'])
    @jwt_required()
    def create_product():
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin', 'researcher']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        product = AgriculturalProduct(
            name=data['name'],
            category=data['category'],
            description=data.get('description')
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify({'message': 'Product created successfully', 'product': product.to_dict()}), 201
    
    # ============ Export Routes ============
    
    @app.route('/api/export/farmers', methods=['GET'])
    @jwt_required()
    def export_farmers():
        try:
            farmers = Farmer.query.all()
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            writer.writerow([
                'Farmer Code', 'First Name', 'Last Name', 'Age', 'Gender', 
                'Education', 'Barangay', 'Municipality', 'Province',
                'Annual Income', 'Farm Size (ha)', 'Years Farming'
            ])
            
            for farmer in farmers:
                b_name = farmer.barangay.name if farmer.barangay else ''
                b_muni = farmer.barangay.municipality if farmer.barangay else ''
                b_prov = farmer.barangay.province if farmer.barangay else ''
                
                writer.writerow([
                    farmer.farmer_code or '',
                    farmer.first_name or '',
                    farmer.last_name or '',
                    farmer.age or '',
                    farmer.gender or '',
                    farmer.education_level or '',
                    b_name,
                    b_muni,
                    b_prov,
                    str(farmer.annual_income) if farmer.annual_income else '',
                    str(farmer.farm_size_hectares) if farmer.farm_size_hectares else '',
                    farmer.years_farming or ''
                ])
            
            csv_data = output.getvalue()
            output.close()
            
            byte_output = io.BytesIO(csv_data.encode('utf-8'))
            
            return send_file(
                byte_output,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'farmers_export_{datetime.now().strftime("%Y%m%d")}.csv'
            )
        except Exception as e:
            print(f"Export Error: {e}")
            return jsonify({'error': 'Failed to generate export file'}), 500
            
    # ============ Users Management Routes ============
    
    @app.route('/api/users', methods=['GET'])
    @jwt_required()
    def get_users():
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        users = User.query.order_by(User.created_at.desc()).all()
        return jsonify([u.to_dict() for u in users]), 200
    
    @app.route('/api/users/<int:id>', methods=['PUT'])
    @jwt_required()
    def update_user(id):
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role not in ['admin']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        user = User.query.get_or_404(id)
        data = request.get_json()
        
        try:
            # Added duplicate checks
            if 'username' in data and data['username'] != user.username:
                if User.query.filter_by(username=data['username']).first():
                    return jsonify({'error': 'Username already taken'}), 400
            
            if 'email' in data and data['email'] != user.email:
                if User.query.filter_by(email=data['email']).first():
                    return jsonify({'error': 'Email already registered'}), 400

            for key, value in data.items():
                if hasattr(user, key) and key not in ['id', 'password_hash', 'created_at', 'password']:
                    setattr(user, key, value)
            
            if 'password' in data and data['password']:
                user.set_password(data['password'])
                
            db.session.commit()
            return jsonify({'message': 'User updated successfully', 'user': user.to_dict()}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    # ADDED DELETE ROUTE HERE
    @app.route('/api/users/<int:id>', methods=['DELETE'])
    @jwt_required()
    def delete_user(id):
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # 1. Permission Check
        if not current_user or current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized: Admin privileges required'}), 403
        
        # 2. Self-Deletion Check
        if int(current_user_id) == id:
            return jsonify({'error': 'System Protocol: Cannot delete active admin account'}), 400

        user_to_delete = User.query.get_or_404(id)
        
        try:
            # 3. UNLINK RELATED RECORDS (The Fix)
            # instead of crashing, we set the 'author' of these records to NULL (Unknown)
            
            # Unlink Farmers encoded by this user
            Farmer.query.filter_by(data_encoder_id=id).update({'data_encoder_id': None})
            
            # Unlink Experiences recorded by this user
            FarmerExperience.query.filter_by(interviewer_id=id).update({'interviewer_id': None})
            
            # Unlink Projects led by this user
            ResearchProject.query.filter_by(principal_investigator_id=id).update({'principal_investigator_id': None})
            
            # Unlink Activity Logs (Keep the history, remove the link)
            ActivityLog.query.filter_by(user_id=id).update({'user_id': None})

            # 4. Execute Deletion
            db.session.delete(user_to_delete)
            db.session.commit()
            
            return jsonify({'message': 'User identity revoked and data unlinked successfully'}), 200
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ DELETE USER ERROR: {str(e)}")
            return jsonify({'error': f'Database Constraint Error: {str(e)}'}), 500
        
        
    
    
    # ============ Activity Logs Routes ============
    
    @app.route('/api/activity-logs', methods=['GET'])
    @jwt_required()
    def get_activity_logs():
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # --- FIX: Allow all authenticated roles to see logs (or at least their own) ---
        if current_user.role not in ['admin', 'researcher', 'data_encoder', 'viewer']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        pagination = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'logs': [log.to_dict() for log in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }), 200
    
    # Initialize DB tables if they don't exist
    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5001, debug=True)