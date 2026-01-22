from flask import Blueprint, request, jsonify
from .. import db

requests_bp = Blueprint('requests', __name__)


@requests_bp.route('', methods=['GET'])
def get_project_requests(project_id):
    """Get requests for a specific project with pagination"""
    try:
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Get pagination parameters
        limit = request.args.get('limit', type=int, default=800)  # Default 800 per page
        page = request.args.get('page', type=int, default=1)  # Default page 1
        offset = (page - 1) * limit if page > 0 else 0
        
        # Get requests with pagination
        requests = db.get_project_requests(project_id, limit=limit, offset=offset)
        
        # Get total count for pagination info
        total_count = db.get_project_requests_count(project_id)
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        
        return jsonify({
            'requests': requests,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@requests_bp.route('/<int:request_id>', methods=['GET'])
def get_project_request(project_id, request_id):
    """Get a specific request from a project"""
    try:
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        req = db.get_project_request(project_id, request_id)
        if not req:
            return jsonify({'error': 'Request not found'}), 404
        
        return jsonify(req), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@requests_bp.route('', methods=['POST'])
def add_project_request(project_id):
    """Add a new request to a project"""
    try:
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.get_json()
        
        # Validation
        if not data or 'method' not in data or 'url' not in data:
            return jsonify({'error': 'Method and URL are required'}), 400
        
        request_id = db.add_request_to_project(
            project_id,
            method=data['method'],
            url=data['url'],
            headers=data.get('headers'),
            body=data.get('body'),
            response_status=data.get('response_status'),
            response_headers=data.get('response_headers'),
            response_body=data.get('response_body')
        )
        
        # Get the created request
        created_request = db.get_project_request(project_id, request_id)
        return jsonify(created_request), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@requests_bp.route('/<int:request_id>', methods=['DELETE'])
def delete_project_request(project_id, request_id):
    """Delete a request from a project"""
    try:
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Verify request exists
        req = db.get_project_request(project_id, request_id)
        if not req:
            return jsonify({'error': 'Request not found'}), 404
        
        db.delete_project_request(project_id, request_id)
        
        return jsonify({'message': 'Request deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@requests_bp.route('', methods=['DELETE'])
def clear_project_requests(project_id):
    """Clear all requests from a project"""
    try:
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        db.clear_project_requests(project_id)
        
        return jsonify({'message': 'All requests cleared successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@requests_bp.route('/filters', methods=['GET'])
def get_project_filters(project_id):
    """Get request filters for a project"""
    try:
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        filters = db.get_project_filters(project_id)
        if filters is None:
            # Return default filters if none exist
            return jsonify({
                'hideStaticAssets': False,
                'excludedHosts': [],
                'includedHosts': [],
                'methods': [],
                'statusCodes': [],
                'textSearch': '',
                'textSearchScope': 'both'
            }), 200
        
        return jsonify(filters), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@requests_bp.route('/filters', methods=['POST'])
def save_project_filters(project_id):
    """Save request filters for a project"""
    try:
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No filter data provided'}), 400
        
        db.save_project_filters(project_id, data)
        
        return jsonify({'message': 'Filters saved successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
