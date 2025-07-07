import requests
import unittest
import uuid
import time
from datetime import datetime

class CarolinaMachadoAPITester(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(CarolinaMachadoAPITester, self).__init__(*args, **kwargs)
        self.base_url = "https://fc73cbc0-1230-45b2-b0ef-c8b44801870e.preview.emergentagent.com/api"
        self.token = None
        self.user_data = None
        self.course_id = None
        
        # Generate unique test data
        timestamp = int(time.time())
        self.test_student = {
            "name": f"Test Student {timestamp}",
            "email": f"student_{timestamp}@test.com",
            "password": "Test@123",
            "user_type": "student"
        }
        
        self.test_instructor = {
            "name": f"Test Instructor {timestamp}",
            "email": f"instructor_{timestamp}@test.com",
            "password": "Test@123",
            "user_type": "instructor"
        }
        
        self.test_course = {
            "title": f"Test Course {timestamp}",
            "description": "This is a test course for API testing",
            "price": 99.99,
            "category": "Enfermagem",
            "level": "iniciante",
            "duration_hours": 10,
            "thumbnail_url": "https://example.com/thumbnail.jpg"
        }

    def test_01_api_root(self):
        """Test the API root endpoint"""
        print("\n🔍 Testing API root endpoint...")
        response = requests.get(f"{self.base_url}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        print("✅ API root endpoint working")

    def test_02_register_student(self):
        """Test student registration"""
        print("\n🔍 Testing student registration...")
        response = requests.post(
            f"{self.base_url}/auth/register",
            json=self.test_student
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["user_type"], "student")
        print(f"✅ Student registration successful: {data['user']['name']}")
        
        # Save token for later tests
        self.student_token = data["token"]
        self.student_data = data["user"]

    def test_03_register_instructor(self):
        """Test instructor registration"""
        print("\n🔍 Testing instructor registration...")
        response = requests.post(
            f"{self.base_url}/auth/register",
            json=self.test_instructor
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["user_type"], "instructor")
        print(f"✅ Instructor registration successful: {data['user']['name']}")
        
        # Save token for later tests
        self.token = data["token"]
        self.user_data = data["user"]

    def test_04_login(self):
        """Test login functionality"""
        print("\n🔍 Testing login...")
        login_data = {
            "email": self.test_instructor["email"],
            "password": self.test_instructor["password"]
        }
        response = requests.post(
            f"{self.base_url}/auth/login",
            json=login_data
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertIn("user", data)
        print(f"✅ Login successful for: {data['user']['email']}")
        
        # Update token
        self.token = data["token"]

    def test_05_get_current_user(self):
        """Test getting current user info"""
        print("\n🔍 Testing get current user info...")
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/auth/me",
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], self.test_instructor["email"])
        print(f"✅ Current user info retrieved: {data['name']}")

    def test_06_create_course(self):
        """Test course creation (as instructor)"""
        print("\n🔍 Testing course creation...")
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/courses",
            json=self.test_course,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("course", data)
        self.course_id = data["course"]["course_id"]
        print(f"✅ Course created: {data['course']['title']}")

    def test_07_get_courses(self):
        """Test getting all courses"""
        print("\n🔍 Testing get all courses...")
        response = requests.get(f"{self.base_url}/courses")
        self.assertEqual(response.status_code, 200)
        courses = response.json()
        self.assertIsInstance(courses, list)
        print(f"✅ Retrieved {len(courses)} courses")

    def test_08_get_course_by_id(self):
        """Test getting a specific course by ID"""
        if not self.course_id:
            self.skipTest("No course ID available")
            
        print(f"\n🔍 Testing get course by ID: {self.course_id}...")
        response = requests.get(f"{self.base_url}/courses/{self.course_id}")
        self.assertEqual(response.status_code, 200)
        course = response.json()
        self.assertEqual(course["course_id"], self.course_id)
        print(f"✅ Retrieved course: {course['title']}")

    def test_09_update_course(self):
        """Test updating a course"""
        if not self.course_id:
            self.skipTest("No course ID available")
            
        print(f"\n🔍 Testing update course: {self.course_id}...")
        headers = {"Authorization": f"Bearer {self.token}"}
        update_data = {
            "title": f"Updated Course {int(time.time())}",
            "price": 129.99
        }
        response = requests.put(
            f"{self.base_url}/courses/{self.course_id}",
            json=update_data,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["course"]["price"], 129.99)
        print(f"✅ Course updated: {data['course']['title']}")

    def test_10_get_instructor_courses(self):
        """Test getting instructor's courses"""
        print("\n🔍 Testing get instructor courses...")
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/instructor/courses",
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        courses = response.json()
        self.assertIsInstance(courses, list)
        print(f"✅ Retrieved {len(courses)} instructor courses")

    def test_11_invalid_login(self):
        """Test invalid login credentials"""
        print("\n🔍 Testing invalid login...")
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        response = requests.post(
            f"{self.base_url}/auth/login",
            json=login_data
        )
        self.assertEqual(response.status_code, 401)
        print("✅ Invalid login correctly rejected")

    def test_12_unauthorized_course_creation(self):
        """Test unauthorized course creation (as student)"""
        print("\n🔍 Testing unauthorized course creation...")
        headers = {"Authorization": f"Bearer {self.student_token}"}
        response = requests.post(
            f"{self.base_url}/courses",
            json=self.test_course,
            headers=headers
        )
        self.assertEqual(response.status_code, 403)
        print("✅ Unauthorized course creation correctly rejected")

def run_tests():
    # Create a test suite
    suite = unittest.TestSuite()
    
    # Add tests in order
    test_cases = [
        'test_01_api_root',
        'test_02_register_student',
        'test_03_register_instructor',
        'test_04_login',
        'test_05_get_current_user',
        'test_06_create_course',
        'test_07_get_courses',
        'test_08_get_course_by_id',
        'test_09_update_course',
        'test_10_get_instructor_courses',
        'test_11_invalid_login',
        'test_12_unauthorized_course_creation'
    ]
    
    for test_case in test_cases:
        suite.addTest(CarolinaMachadoAPITester(test_case))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n📊 Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == "__main__":
    print("🧪 Starting Carolina Machado Platform API Tests")
    success = run_tests()
    print("✅ All tests passed!" if success else "❌ Some tests failed!")