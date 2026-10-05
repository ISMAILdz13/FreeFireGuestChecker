"""
Dashboard routes for Free Fire Guest Account Checker
Advanced analytics and statistics
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, render_template, request, jsonify, current_app

from config.settings import get_settings
from src.database.database import get_database
from src.utils.helpers import format_timestamp, get_timestamp
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Create dashboard blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard', 
                        template_folder='../templates', static_folder='../static')


@dashboard_bp.route('/')
def dashboard_index():
    """Main dashboard page"""
    db = get_database()
    settings = get_settings()
    
    # Get statistics
    stats = db.get_statistics_sync() if hasattr(db, 'get_statistics_sync') else {}
    
    # Get recent activity
    recent_accounts = []
    if hasattr(db, 'get_recent_accounts_sync'):
        recent_accounts = db.get_recent_accounts_sync(limit=10)
    
    # Get status distribution
    status_dist = {}
    if hasattr(db, 'get_status_distribution_sync'):
        status_dist = db.get_status_distribution_sync()
    
    return render_template('dashboard/index.html',
                         stats=stats,
                         recent_accounts=recent_accounts,
                         status_dist=status_dist,
                         app_name="FreeFire Guest Checker",
                         version="2.0.0")


@dashboard_bp.route('/analytics')
def analytics_page():
    """Analytics page with charts"""
    db = get_database()
    
    # Get time series data
    time_series = []
    if hasattr(db, 'get_checks_by_date_sync'):
        # Last 30 days
        for i in range(30):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            count = db.get_checks_by_date_sync(date)
            time_series.append({'date': date, 'count': count})
    
    # Get region distribution
    region_dist = {}
    if hasattr(db, 'get_region_distribution_sync'):
        region_dist = db.get_region_distribution_sync()
    
    # Get source distribution
    source_dist = {}
    if hasattr(db, 'get_source_distribution_sync'):
        source_dist = db.get_source_distribution_sync()
    
    return render_template('dashboard/analytics.html',
                         time_series=time_series,
                         region_dist=region_dist,
                         source_dist=source_dist,
                         app_name="FreeFire Guest Checker")


@dashboard_bp.route('/accounts')
def dashboard_accounts():
    """Accounts page with advanced filtering"""
    db = get_database()
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    status = request.args.get('status', None)
    region = request.args.get('region', None)
    search = request.args.get('search', None)
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    offset = (page - 1) * per_page
    
    accounts, total = db.list_accounts_sync(
        offset=offset,
        limit=per_page,
        status=status,
        region=region,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order
    ) if hasattr(db, 'list_accounts_sync') else ([], 0)
    
    return render_template('dashboard/accounts.html',
                         accounts=accounts,
                         total=total,
                         page=page,
                         per_page=per_page,
                         status=status,
                         region=region,
                         search=search,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         app_name="FreeFire Guest Checker")


@dashboard_bp.route('/account/<account_id>')
def account_detail_dashboard(account_id: str):
    """Account detail page"""
    db = get_database()
    
    account = db.get_account_sync(account_id) if hasattr(db, 'get_account_sync') else None
    
    if not account:
        return render_template('error.html', 
                             message=f"Account {account_id} not found",
                             code=404),
    
    # Get check history
    history = []
    if hasattr(db, 'get_account_history_sync'):
        history = db.get_account_history_sync(account_id)
    
    return render_template('dashboard/account_detail.html',
                         account=account,
                         history=history,
                         app_name="FreeFire Guest Checker")


@dashboard_bp.route('/api/analytics/overview')
def analytics_overview_api():
    """Get overview analytics"""
    db = get_database()
    
    stats = db.get_statistics_sync() if hasattr(db, 'get_statistics_sync') else {}
    
    # Get time series data
    time_series = []
    if hasattr(db, 'get_checks_by_date_sync'):
        for i in range(30):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            count = db.get_checks_by_date_sync(date)
            time_series.append({'date': date, 'count': count})
    
    return jsonify({
        'stats': stats,
        'time_series': time_series,
        'timestamp': get_timestamp()
    })


@dashboard_bp.route('/api/analytics/status-distribution')
def status_distribution_api():
    """Get status distribution"""
    db = get_database()
    
    status_dist = {}
    if hasattr(db, 'get_status_distribution_sync'):
        status_dist = db.get_status_distribution_sync()
    
    return jsonify({
        'distribution': status_dist,
        'timestamp': get_timestamp()
    })


@dashboard_bp.route('/api/analytics/region-distribution')
def region_distribution_api():
    """Get region distribution"""
    db = get_database()
    
    region_dist = {}
    if hasattr(db, 'get_region_distribution_sync'):
        region_dist = db.get_region_distribution_sync()
    
    return jsonify({
        'distribution': region_dist,
        'timestamp': get_timestamp()
    })


@dashboard_bp.route('/api/analytics/source-distribution')
def source_distribution_api():
    """Get source distribution"""
    db = get_database()
    
    source_dist = {}
    if hasattr(db, 'get_source_distribution_sync'):
        source_dist = db.get_source_distribution_sync()
    
    return jsonify({
        'distribution': source_dist,
        'timestamp': get_timestamp()
    })


@dashboard_bp.route('/api/accounts/export')
def export_accounts_api():
    """Export accounts as JSON or CSV"""
    db = get_database()
    
    format_type = request.args.get('format', 'json')
    status = request.args.get('status', None)
    region = request.args.get('region', None)
    
    accounts, _ = db.list_accounts_sync(
        offset=0,
        limit=10000,
        status=status,
        region=region
    ) if hasattr(db, 'list_accounts_sync') else ([], 0)
    
    if format_type == 'csv':
        # Generate CSV
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['account_id', 'status', 'region', 'source', 'created_at', 'updated_at', 'data'])
        
        # Write data
        for acc in accounts:
            data_str = json.dumps(acc.data) if hasattr(acc, 'data') else ''
            writer.writerow([
                acc.account_id,
                acc.status.value if hasattr(acc, 'status') else '',
                acc.region if hasattr(acc, 'region') else '',
                acc.source if hasattr(acc, 'source') else '',
                format_timestamp(acc.created_at) if hasattr(acc, 'created_at') else '',
                format_timestamp(acc.updated_at) if hasattr(acc, 'updated_at') else '',
                data_str
            ])
        
        return output.getvalue(), 200, {'Content-Type': 'text/csv', 
                                        'Content-Disposition': 'attachment; filename=accounts.csv'}
    else:
        # Return as JSON
        accounts_list = [acc.to_dict() for acc in accounts]
        return jsonify({
            'accounts': accounts_list,
            'count': len(accounts_list),
            'exported_at': get_timestamp()
        })


@dashboard_bp.route('/api/accounts/import', methods=['POST'])
def import_accounts_api():
    """Import accounts from JSON or CSV"""
    db = get_database()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    format_type = request.form.get('format', 'json')
    
    if format_type == 'csv':
        import csv
        from io import StringIO
        
        content = file.read().decode('utf-8')
        reader = csv.DictReader(StringIO(content))
        
        imported = 0
        for row in reader:
            account_id = row.get('account_id')
            if account_id:
                data = {}
                if 'data' in row and row['data']:
                    try:
                        data = json.loads(row['data'])
                    except:
                        pass
                
                db.save_account_sync(
                    account_id=account_id,
                    data=data,
                    region=row.get('region', 'imported'),
                    source=row.get('source', 'csv_import')
                ) if hasattr(db, 'save_account_sync') else None
                imported += 1
        
        return jsonify({'imported': imported, 'timestamp': get_timestamp()})
    else:
        # JSON format
        data = json.loads(file.read().decode('utf-8'))
        accounts = data.get('accounts', [])
        
        imported = 0
        for acc in accounts:
            account_id = acc.get('account_id')
            if account_id:
                db.save_account_sync(
                    account_id=account_id,
                    data=acc.get('data', {}),
                    region=acc.get('region', 'imported'),
                    source=acc.get('source', 'json_import')
                ) if hasattr(db, 'save_account_sync') else None
                imported += 1
        
        return jsonify({'imported': imported, 'timestamp': get_timestamp()})


@dashboard_bp.route('/settings')
def dashboard_settings():
    """Dashboard settings page"""
    settings = get_settings()
    
    return render_template('dashboard/settings.html',
                         settings=settings,
                         app_name="FreeFire Guest Checker")


@dashboard_bp.route('/logs')
def dashboard_logs():
    """View application logs"""
    import glob
    
    log_files = []
    log_dir = 'logs'
    
    if os.path.exists(log_dir):
        for file in glob.glob(os.path.join(log_dir, '*.log')):
            log_files.append({
                'name': os.path.basename(file),
                'path': file,
                'size': os.path.getsize(file),
                'modified': datetime.fromtimestamp(os.path.getmtime(file)).strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return render_template('dashboard/logs.html',
                         log_files=log_files,
                         app_name="FreeFire Guest Checker")


@dashboard_bp.route('/logs/<filename>')
def view_log_file(filename: str):
    """View a specific log file"""
    log_dir = 'logs'
    file_path = os.path.join(log_dir, filename)
    
    if not os.path.exists(file_path):
        return render_template('error.html', message='Log file not found', code=404)
    
    # Read last 1000 lines
    with open(file_path, 'r') as f:
        lines = f.readlines()[-1000:]
    
    return render_template('dashboard/log_viewer.html',
                         filename=filename,
                         lines=lines,
                         app_name="FreeFire Guest Checker")
