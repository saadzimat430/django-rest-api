from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """ Test the users API """

    def setUp(self):
        self.client = APIClient()

    def test_create_valid_user_successful(self):
        """ Test creating user with valid payload is successful """
        payload = {
            'email': 'test@gmail.com',
            'password': 'test123',
            'name': 'Test Name',
        }
        response = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(**response.data)
        self.assertTrue(user.check_password(payload['password']))
        # password is not returned as part of response (security vulnerability)
        self.assertNotIn('password', response.data)

    def test_user_exists(self):
        """ Test creating user that already exists fails """
        payload = {
            'email': 'test@gmail.com',
            'password': 'test123',
            'name': 'Test Name',
        }
        # is similar to create_user(email='test@gmail.com', password='test123
        create_user(**payload)

        response = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        """ Test that password must be more than 5 chars """
        payload = {
            'email': 'test@gmail.com',
            'password': 'pw',
            'name': 'Test Name',
        }
        response = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """ Test that a token is created for the user """
        payload = {'email': 'test@gmail.com', 'password': 'testpass'}
        create_user(**payload)
        response = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_token_invalid_credentials(self):
        """ Test that token is not created if credentials are invalid """
        create_user(email='test@gmail.com', password='testpass')
        payload = {'email': 'test@gmail.com', 'password': 'wrong'}
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_no_user(self):
        """ test token is not created if user is not existing """
        payload = {'email': 'test@gmail.com', 'password': 'testpass'}
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_missing_field(self):
        """ Test email and password are required """
        res = self.client.post(TOKEN_URL, {'email': 'one', 'password': ''})

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """ Test authentication is required for users """
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    """ test API requests that require authentication """

    def setUp(self):
        self.user = create_user(
            email='test@gmail.com',
            password='testpass',
            name='name',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """ Test retrieving profile for logged in user """
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'name': self.user.name,
            'email': self.user.email
        })

    def test_post_not_allowed(self):
        """ test that POST is not allowed on ME url """
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """ test updating user profile for authenticated user """
        payload = {
            'name': 'new name',
            'password': 'newpassword123'
        }

        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
