from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class HealthCheck(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bp = models.IntegerField()
    cholesterol = models.IntegerField()
    sugar_level = models.IntegerField()  # New field
    # exercise_minutes = models.IntegerField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.date}"

    

class DailyCheck(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    heart_rate = models.IntegerField()
    spo2 = models.IntegerField()
    exercise_minutes = models.IntegerField()
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.date}"
    

class PredictionHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    result = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.result} @ {self.timestamp}"
    



