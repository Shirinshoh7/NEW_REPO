"""
AI сервис для прогнозирования
"""
from typing import List


class AIService:
    """Сервис AI прогнозов"""
    
    @staticmethod
    def predict_linear(data_points: List[float]) -> float:
        """
        Линейная регрессия для прогноза
        
        Args:
            data_points: Список исторических значений
            
        Returns:
            Прогнозируемое значение
        """
        if len(data_points) < 5:
            return data_points[-1] if data_points else 0.0
        
        n = len(data_points)
        sum_x = sum_y = sum_xy = sum_xx = 0
        
        for i in range(n):
            sum_x += i
            sum_y += data_points[i]
            sum_xy += i * data_points[i]
            sum_xx += i * i
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n
        
        # Прогноз на 5 шагов вперед
        prediction = slope * (n + 5) + intercept
        
        return round(prediction, 1)
    
    @staticmethod
    def calculate_mc_score(current_data: dict, profile: dict) -> int:
        """
        Расчет MicroClimate Score (0-100)
        
        Args:
            current_data: Текущие данные
            profile: Активный профиль
            
        Returns:
            MC Score от 0 до 100
        """
        if current_data["timestamp"] is None:
            return 0
        
        score = 100
        temp = current_data["temperature"]
        hum = current_data["humidity"]
        co2 = current_data["co2_ppm"]
        lux = current_data["lux"]
        
        # Штрафы за выход из нормы
        if temp < profile["temp_min"] or temp > profile["temp_max"]:
            score -= 15
        if hum > profile["humidity_max"]:
            score -= 15
        if co2 > profile["co2_max"]:
            score -= 20
        if lux < profile["lux_min"] or lux > profile["lux_max"]:
            score -= 10
        
        return max(0, min(100, score))


# Глобальный экземпляр сервиса
ai_service = AIService()
