# tests/test_data_processing.py
"""
Unit тесты для модуля предобработки данных (shared/data_processing.py)
"""

import pytest
import pandas as pd
import numpy as np

from shared.data_processing import (
    feature_engineering,
    preprocess_data,
    preprocess_data_for_prediction
)


class TestFeatureEngineering:
    """Тесты для feature engineering"""
    
    def test_feature_engineering_adds_ratio(self):
        """Тест добавления loan_to_income_ratio"""
        df = pd.DataFrame({
            "loan_amnt": [10000, 20000, 30000],
            "person_income": [50000, 100000, 150000]
        })
        
        result = feature_engineering(df)
        
        assert "loan_to_income_ratio" in result.columns
        assert result["loan_to_income_ratio"].iloc[0] == 0.2
        assert result["loan_to_income_ratio"].iloc[1] == 0.2
        assert result["loan_to_income_ratio"].iloc[2] == 0.2
    
    def test_feature_engineering_preserves_original(self):
        """Тест сохранения исходных колонок"""
        df = pd.DataFrame({
            "loan_amnt": [10000],
            "person_income": [50000],
            "person_age": [35]
        })
        
        result = feature_engineering(df)
        
        assert "loan_amnt" in result.columns
        assert "person_income" in result.columns
        assert "person_age" in result.columns
        assert "loan_to_income_ratio" in result.columns
    
    def test_feature_engineering_does_not_modify_original(self):
        """Тест, что исходный DataFrame не изменяется"""
        df = pd.DataFrame({
            "loan_amnt": [10000],
            "person_income": [50000]
        })
        original_columns = df.columns.tolist()
        
        result = feature_engineering(df)
        
        assert df.columns.tolist() == original_columns
        assert "loan_to_income_ratio" not in df.columns


class TestPreprocessData:
    """Тесты для предобработки данных для обучения"""
    
    def test_preprocess_data_creates_features(self):
        """Тест создания признаков при предобработке"""
        df = pd.DataFrame({
            "person_age": [35, 40],
            "person_income": [75000, 80000],
            "person_home_ownership": ["RENT", "OWN"],
            "person_emp_length": [5.0, 10.0],
            "loan_intent": ["DEBTCONSOLIDATION", "EDUCATION"],
            "loan_grade": ["B", "A"],
            "loan_amnt": [20000, 25000],
            "loan_int_rate": [9.5, 8.5],
            "loan_percent_income": [0.27, 0.31],
            "cb_person_default_on_file": ["N", "N"],
            "cb_person_cred_hist_length": [4, 5],
            "loan_status": [0, 0]
        })
        
        X, y = preprocess_data(df)
        
        # Проверяем, что X и y разделены
        assert "loan_status" not in X.columns
        assert "loan_status" in y.name
        
        # Проверяем, что категориальные признаки закодированы
        assert "person_home_ownership" not in X.columns
        assert "loan_intent" not in X.columns
        assert "loan_grade" not in X.columns
        assert "cb_person_default_on_file" not in X.columns
        
        # Проверяем наличие OHE колонок
        assert any("person_home_ownership_" in col for col in X.columns)
        assert any("loan_intent_" in col for col in X.columns)
        assert any("loan_grade_" in col for col in X.columns)
    
    def test_preprocess_data_creates_ratio(self):
        """Тест создания loan_to_income_ratio"""
        df = pd.DataFrame({
            "person_age": [35],
            "person_income": [75000],
            "person_home_ownership": ["RENT"],
            "person_emp_length": [5.0],
            "loan_intent": ["DEBTCONSOLIDATION"],
            "loan_grade": ["B"],
            "loan_amnt": [20000],
            "loan_int_rate": [9.5],
            "loan_percent_income": [0.27],
            "cb_person_default_on_file": ["N"],
            "cb_person_cred_hist_length": [4],
            "loan_status": [0]
        })
        
        X, y = preprocess_data(df)
        
        assert "loan_to_income_ratio" in X.columns
    
    def test_preprocess_data_returns_correct_shapes(self):
        """Тест правильности размеров X и y"""
        df = pd.DataFrame({
            "person_age": [35, 40, 45],
            "person_income": [75000, 80000, 85000],
            "person_home_ownership": ["RENT", "OWN", "MORTGAGE"],
            "person_emp_length": [5.0, 10.0, 15.0],
            "loan_intent": ["DEBTCONSOLIDATION", "EDUCATION", "MEDICAL"],
            "loan_grade": ["B", "A", "C"],
            "loan_amnt": [20000, 25000, 30000],
            "loan_int_rate": [9.5, 8.5, 10.5],
            "loan_percent_income": [0.27, 0.31, 0.35],
            "cb_person_default_on_file": ["N", "N", "Y"],
            "cb_person_cred_hist_length": [4, 5, 6],
            "loan_status": [0, 0, 1]
        })
        
        X, y = preprocess_data(df)
        
        assert len(X) == 3
        assert len(y) == 3
        assert len(X) == len(y)


class TestPreprocessDataForPrediction:
    """Тесты для предобработки данных для предсказания"""
    
    def test_preprocess_data_for_prediction_creates_features(self, sample_loan_request):
        """Тест создания признаков для предсказания"""
        df = pd.DataFrame([sample_loan_request])
        
        result = preprocess_data_for_prediction(df)
        
        # Проверяем, что категориальные признаки закодированы
        assert "person_home_ownership" not in result.columns
        assert "loan_intent" not in result.columns
        assert "loan_grade" not in result.columns
        
        # Проверяем наличие OHE колонок
        assert any("person_home_ownership_" in col for col in result.columns)
        assert any("loan_intent_" in col for col in result.columns)
        assert any("loan_grade_" in col for col in result.columns)
    
    def test_preprocess_data_for_prediction_creates_ratio(self, sample_loan_request):
        """Тест создания loan_to_income_ratio"""
        df = pd.DataFrame([sample_loan_request])
        
        result = preprocess_data_for_prediction(df)
        
        assert "loan_to_income_ratio" in result.columns
        expected_ratio = sample_loan_request["loan_amnt"] / sample_loan_request["person_income"]
        assert result["loan_to_income_ratio"].iloc[0] == pytest.approx(expected_ratio)
    
    def test_preprocess_data_for_prediction_handles_missing_features(self, sample_loan_request):
        """Тест обработки отсутствующих признаков"""
        df = pd.DataFrame([sample_loan_request])
        
        result = preprocess_data_for_prediction(df)
        
        # Проверяем, что результат является DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

