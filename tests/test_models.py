# tests/test_models.py
"""
Unit тесты для моделей данных (shared/models.py)
"""

import pytest
from pydantic import ValidationError

from shared.models import (
    LoanRequest,
    FeedbackRequest,
    LoginRequest as AuthLoginRequest,
    Token,
    TokenRefresh,
    UserInfo
)


class TestLoanRequest:
    """Тесты для модели LoanRequest"""
    
    def test_loan_request_valid(self, sample_loan_request):
        """Тест создания валидного запроса на кредит"""
        request = LoanRequest(**sample_loan_request)
        
        assert request.person_age == 35
        assert request.person_income == 75000
        assert request.person_home_ownership == "RENT"
        assert request.loan_grade == "B"
    
    def test_loan_request_missing_field(self, sample_loan_request):
        """Тест создания запроса с отсутствующим полем"""
        del sample_loan_request["person_age"]
        
        with pytest.raises(ValidationError):
            LoanRequest(**sample_loan_request)
    
    def test_loan_request_wrong_type(self, sample_loan_request):
        """Pydantic V2 по умолчанию приводит типы, поэтому проверяем коэрцию"""
        sample_loan_request["person_age"] = "35"  # Строка
        request = LoanRequest(**sample_loan_request)
        assert isinstance(request.person_age, int)
        assert request.person_age == 35
    
    def test_loan_request_model_dump(self, sample_loan_request):
        """Тест сериализации модели"""
        request = LoanRequest(**sample_loan_request)
        data = request.model_dump()
        
        assert isinstance(data, dict)
        assert data["person_age"] == 35
        assert data["person_income"] == 75000


class TestFeedbackRequest:
    """Тесты для модели FeedbackRequest"""
    
    def test_feedback_request_valid(self, sample_feedback_request):
        """Тест создания валидного фидбэка"""
        request = FeedbackRequest(**sample_feedback_request)
        
        assert request.predicted_status == 0
        assert request.actual_status == 1
        assert request.probability_repaid == 0.92
        assert request.probability_default == 0.08
    
    def test_feedback_request_inherits_loan_request(self, sample_feedback_request):
        """Тест наследования от LoanRequest"""
        request = FeedbackRequest(**sample_feedback_request)
        
        # Проверяем, что поля из LoanRequest доступны
        assert request.person_age == 35
        assert request.person_income == 75000
    
    def test_feedback_request_optional_probabilities(self, sample_loan_request):
        """Тест создания фидбэка с опциональными вероятностями"""
        data = sample_loan_request.copy()
        data.update({
            "predicted_status": 0,
            "actual_status": 1
        })
        
        request = FeedbackRequest(**data)
        assert request.probability_repaid is None
        assert request.probability_default is None


class TestAuthModels:
    """Тесты для моделей авторизации"""
    
    def test_login_request_valid(self):
        """Тест создания валидного запроса на логин"""
        request = AuthLoginRequest(username="testuser", password="testpass123")
        
        assert request.username == "testuser"
        assert request.password == "testpass123"
    
    def test_login_request_missing_field(self):
        """Тест создания запроса с отсутствующим полем"""
        with pytest.raises(ValidationError):
            AuthLoginRequest(username="testuser")
    
    def test_token_valid(self):
        """Тест создания валидного токена"""
        token = Token(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_type="bearer"
        )
        
        assert token.access_token == "test_access_token"
        assert token.refresh_token == "test_refresh_token"
        assert token.token_type == "bearer"
    
    def test_token_default_type(self):
        """Тест создания токена с дефолтным типом"""
        token = Token(
            access_token="test_access_token",
            refresh_token="test_refresh_token"
        )
        
        assert token.token_type == "bearer"
    
    def test_token_refresh_valid(self):
        """Тест создания валидного запроса на обновление токена"""
        request = TokenRefresh(refresh_token="test_refresh_token")
        
        assert request.refresh_token == "test_refresh_token"
    
    def test_user_info_valid(self, test_user):
        """Тест создания валидной информации о пользователе"""
        user_info = UserInfo(
            id=test_user.id,
            username=test_user.username,
            role=test_user.role,
            is_active=test_user.is_active
        )
        
        assert user_info.id == test_user.id
        assert user_info.username == test_user.username
        assert user_info.role == test_user.role
        assert user_info.is_active is True
    
    def test_user_info_from_attributes(self, test_user):
        """Тест создания UserInfo из ORM модели"""
        user_info = UserInfo.model_validate(test_user)
        
        assert user_info.id == test_user.id
        assert user_info.username == test_user.username
        assert user_info.role == test_user.role

