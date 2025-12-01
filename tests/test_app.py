"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities

# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        },
    })
    yield
    # Cleanup after test
    activities.clear()


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_success(self):
        """Test successfully fetching all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert data["Chess Club"]["max_participants"] == 12
        assert len(data["Chess Club"]["participants"]) == 2

    def test_get_activities_contains_participant_info(self):
        """Test that activities contain participant information"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in data["message"]

    def test_signup_adds_participant_to_activity(self):
        """Test that signup actually adds the participant to the activity"""
        new_email = "newstudent@mergington.edu"
        client.post(f"/activities/Chess Club/signup?email={new_email}")

        response = client.get("/activities")
        data = response.json()
        assert new_email in data["Chess Club"]["participants"]
        assert len(data["Chess Club"]["participants"]) == 3

    def test_signup_activity_not_found(self):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_already_registered(self):
        """Test signing up a student who is already registered"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_preserves_existing_participants(self):
        """Test that signup doesn't remove existing participants"""
        original_participants = activities["Chess Club"]["participants"].copy()

        client.post("/activities/Chess Club/signup?email=newstudent@mergington.edu")

        response = client.get("/activities")
        data = response.json()
        for participant in original_participants:
            assert participant in data["Chess Club"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self):
        """Test successful unregistration from an activity"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert "michael@mergington.edu" in data["message"]

    def test_unregister_removes_participant_from_activity(self):
        """Test that unregister actually removes the participant"""
        client.delete("/activities/Chess Club/unregister?email=michael@mergington.edu")

        response = client.get("/activities")
        data = response.json()
        assert "michael@mergington.edu" not in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]
        assert len(data["Chess Club"]["participants"]) == 1

    def test_unregister_activity_not_found(self):
        """Test unregistering from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_not_registered(self):
        """Test unregistering a student who is not registered"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]

    def test_unregister_preserves_other_participants(self):
        """Test that unregister doesn't remove other participants"""
        client.delete("/activities/Chess Club/unregister?email=michael@mergington.edu")

        response = client.get("/activities")
        data = response.json()
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]

    def test_unregister_then_signup_again(self):
        """Test that a student can unregister and sign up again"""
        email = "michael@mergington.edu"

        # Unregister
        response = client.delete(f"/activities/Chess Club/unregister?email={email}")
        assert response.status_code == 200

        # Sign up again
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response.status_code == 200

        # Verify participant is back in the list
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]


class TestRootEndpoint:
    """Tests for root endpoint"""

    def test_root_redirect(self):
        """Test that root endpoint redirects to static page"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestActivityIntegration:
    """Integration tests for multiple operations"""

    def test_signup_multiple_students(self):
        """Test signing up multiple students to the same activity"""
        emails = [
            "alice@mergington.edu",
            "bob@mergington.edu",
            "charlie@mergington.edu",
        ]

        for email in emails:
            response = client.post(f"/activities/Programming Class/signup?email={email}")
            assert response.status_code == 200

        response = client.get("/activities")
        data = response.json()
        for email in emails:
            assert email in data["Programming Class"]["participants"]

    def test_mixed_operations(self):
        """Test a sequence of signup and unregister operations"""
        # Initial state: 2 participants
        email1 = "newstudent1@mergington.edu"
        email2 = "newstudent2@mergington.edu"

        # Sign up two new students
        client.post(f"/activities/Gym Class/signup?email={email1}")
        client.post(f"/activities/Gym Class/signup?email={email2}")

        response = client.get("/activities")
        data = response.json()
        assert len(data["Gym Class"]["participants"]) == 4

        # Unregister one student
        client.delete(f"/activities/Gym Class/unregister?email={email1}")

        response = client.get("/activities")
        data = response.json()
        assert len(data["Gym Class"]["participants"]) == 3
        assert email1 not in data["Gym Class"]["participants"]
        assert email2 in data["Gym Class"]["participants"]
