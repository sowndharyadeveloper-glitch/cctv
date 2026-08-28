import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import cv2
import numpy as np
from werkzeug.security import generate_password_hash

from config import BASE_DIR
from database import db


class DatabaseSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        db.DB_PATH = self.temp_db.name

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def test_default_admin_created_with_hash(self):
        db.init_db()
        db.ensure_default_admin('admin', generate_password_hash('admin123', method='pbkdf2:sha256:150000'))
        conn = sqlite3.connect(self.temp_db.name)
        row = conn.execute(
            "SELECT username, password_hash FROM admin_users WHERE username = 'admin'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertTrue(row[1].startswith('pbkdf2:'))

    def test_students_schema_has_required_fields(self):
        db.init_db()
        conn = sqlite3.connect(self.temp_db.name)
        cols = conn.execute("PRAGMA table_info(students)").fetchall()
        conn.close()
        names = {row[1] for row in cols}
        self.assertIn('email', names)
        self.assertIn('phone', names)
        self.assertIn('face_encoding', names)

    def test_cameras_schema_and_crud(self):
        db.init_db()
        camera_id = db.add_camera({
            'name': 'Mobile test camera',
            'camera_type': 'mobile_ip_camera',
            'stream_url': 'http://192.168.1.20:8080/video',
            'location': 'Loading bay',
            'department': 'Security',
        })
        self.assertIsNotNone(camera_id)
        camera = db.get_camera_by_id(camera_id)
        self.assertEqual(camera['camera_type'], 'mobile_ip_camera')
        db.update_camera_status(camera_id, 'offline', 'Stream unavailable')
        self.assertEqual(db.get_camera_by_id(camera_id)['status'], 'offline')
        db.delete_camera(camera_id)
        self.assertIsNone(db.get_camera_by_id(camera_id))

    def test_safety_alert_cooldown_and_lifecycle(self):
        db.init_db()
        camera_id = db.add_camera({'name': 'Safety camera', 'stream_url': '0'})
        event = {
            'alert_type': 'PPE_VIOLATION',
            'severity': 'HIGH',
            'camera_id': camera_id,
            'zone_id': 'WELDING-AREA',
            'tracking_id': 'TRACK-01',
            'confidence': 91.0,
            'description': 'Missing helmet',
            'simulated': True,
        }
        alert_id = db.create_safety_alert(event)
        self.assertIsNotNone(alert_id)
        self.assertIsNone(db.create_safety_alert(event))
        self.assertTrue(db.update_alert_status(alert_id, 'ACKNOWLEDGED', 'admin'))
        self.assertTrue(db.update_alert_status(alert_id, 'RESOLVED', 'admin', 'Corrected PPE'))
        self.assertEqual(db.get_safety_alerts()[0]['status'], 'RESOLVED')

    def test_zone_geometry_is_persisted_and_invalid_api_payload_is_rejected(self):
        db.init_db()
        camera_id = db.add_camera({'name': 'Zone camera', 'stream_url': '0'})
        zone_id = db.add_zone({'camera_id': camera_id, 'name': 'Machine room', 'geometry_json': '[{"x": 10, "y": 20}, {"x": 30, "y": 20}, {"x": 20, "y": 40}]', 'required_ppe_json': '["Helmet"]'})
        self.assertIsNotNone(zone_id)
        self.assertEqual(db.get_zone_by_id(zone_id)['name'], 'Machine room')

        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import app as app_module
        db.ensure_default_admin('admin', generate_password_hash('admin123', method='pbkdf2:sha256:150000'))
        client = app_module.app.test_client()
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        response = client.post('/api/zones', json={'camera_id': camera_id, 'name': 'Invalid', 'geometry': [{'x': 1, 'y': 2}]})
        self.assertEqual(response.status_code, 400)

    def test_frame_analysis_creates_intrusion_alerts(self):
        db.init_db()
        camera_id = db.add_camera({'name': 'Analysis camera', 'stream_url': '0'})
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import app as app_module
        db.ensure_default_admin('admin', generate_password_hash('admin123', method='pbkdf2:sha256:150000'))
        client = app_module.app.test_client()
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        success, encoded = cv2.imencode('.jpg', np.zeros((40, 40, 3), dtype=np.uint8))
        image = 'data:image/jpeg;base64,' + __import__('base64').b64encode(encoded.tobytes()).decode('ascii')
        analysis = {'detections': [{'x': 10, 'y': 10, 'width': 20, 'height': 20}], 'intrusions': [{'zone_id': 4, 'zone_name': 'Machine room', 'severity': 'HIGH', 'tracking_id': 'FRAME-PERSON-1', 'confidence': 88.0}]}
        with patch.object(app_module, 'detect_people_in_zones', return_value=analysis):
            response = client.post(f'/api/cameras/{camera_id}/analyze', json={'image': image})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()['alert_ids']), 1)

    def test_camera_api_validates_and_does_not_expose_stream_url(self):
        db.init_db()
        db.ensure_default_admin('admin', generate_password_hash('admin123', method='pbkdf2:sha256:150000'))
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import app as app_module

        client = app_module.app.test_client()
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        invalid = client.post('/api/cameras', json={'name': 'Bad', 'stream_url': 'ftp://invalid'})
        self.assertEqual(invalid.status_code, 400)
        client.post('/api/cameras', json={'name': 'Good', 'stream_url': 'http://192.168.1.20:8080/video'})
        cameras = client.get('/api/cameras').get_json()['data']
        self.assertNotIn('stream_url', cameras[0])

        missing = client.post('/api/cameras', json={'name': 'Missing URL'})
        self.assertEqual(missing.status_code, 400)

    def test_monitoring_and_stream_routes_are_authenticated(self):
        db.init_db()
        db.ensure_default_admin('admin', generate_password_hash('admin123', method='pbkdf2:sha256:150000'))
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import app as app_module

        client = app_module.app.test_client()
        self.assertEqual(client.get('/monitoring').status_code, 302)
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        self.assertEqual(client.get('/monitoring').status_code, 200)
        self.assertEqual(client.get('/api/cameras/999/stream').status_code, 404)

    def test_live_camera_page_uses_browser_capture_and_login_redirects(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import app as app_module

        db.init_db()
        db.ensure_default_admin('admin', generate_password_hash('admin123'))
        client = app_module.app.test_client()
        login_response = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=False)
        self.assertEqual(login_response.status_code, 302)
        self.assertIn('/dashboard', login_response.headers.get('Location', ''))

        camera_response = client.get('/live-camera')
        self.assertEqual(camera_response.status_code, 200)
        camera_html = camera_response.get_data(as_text=True)
        self.assertIn('navigator.mediaDevices', camera_html)
        self.assertIn('/live-camera/recognize', camera_html)
        self.assertIn('video', camera_html.lower())


if __name__ == '__main__':
    unittest.main()
