from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from .models import HealthCheck, DailyCheck, PredictionHistory
from .forms import HealthCheckForm, DailyCheckForm
import json
from .forms import PDFUploadForm
import fitz  # PyMuPDF
import re
import joblib
import numpy as np


# Create your views here.
def home_view(request):
    return render(request, 'prediction/landing_page.html')


def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')  
        else:
            messages.error(request, 'Invalid username or password')

    return render(request, 'prediction/login_page.html')

def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Auto-login after registration
            return redirect("login")  # Redirect after successful registration
    else:
        form = UserCreationForm()
    return render(request, "prediction/register.html", {"form": form})
#-------------------------------------------------------------------------------------#
#  Load model & scaler
model = joblib.load("prediction/trained_model.pkl")
scaler = joblib.load("prediction/scaler.pkl")

def predict_heart_disease_from_pdf(request):
    prediction = None
    if request.method == "POST":
        form = PDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_file = request.FILES['report']
            pdf_bytes = pdf_file.read()
            text = extract_text_from_pdf_bytes(pdf_bytes)
            patient_data = parse_medical_data(text)
            features = np.array(list(patient_data.values())).reshape(1, -1)

            # Check feature size
            if features.shape[1] != scaler.n_features_in_:
                prediction = "⚠ Error: Feature count mismatch. Check report formatting."
            else:
                features_scaled = scaler.transform(features)
                result = model.predict(features_scaled)[0]
                prediction = "🟥 High risk of heart disease" if result == 1 else "🟩 Low risk of heart disease"
                if request.user.is_authenticated:
                    PredictionHistory.objects.create(user=request.user, result=prediction)
            request.session['prediction'] = prediction  # 🔁 store in session
            return redirect('predict')  # 🔁 redirect to avoid resubmit
    else:
        form = PDFUploadForm()
    prediction = request.session.pop('prediction', None)  # ⏪ retrieve once then remove
    history = []
    if request.user.is_authenticated:
        history = PredictionHistory.objects.filter(user=request.user).order_by('-timestamp')[:5]  
    return render(request, "prediction/predict.html", {
        "form": form,
        "prediction": prediction if prediction else None,
        "history": history
    })

def extract_text_from_pdf_bytes(pdf_bytes):
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        text = "\n".join(page.get_text("text") for page in doc)
    return text

def extract_value(pattern, text, default=None, dtype=int):
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if match:
        try:
            return dtype(match.group(1).strip())
        except ValueError:
            return default
    else:
        return default

def parse_medical_data(text):
    text = re.sub(r"\s+", " ", text)
    text = text.replace(":", " ")
    text = text.lower()

    data = {
        "age": extract_value(r"age\s*[:\s]+(\d+)", text, default=50, dtype=int),
        "sex": 1 if extract_value(r"sex\s*[:\s]+(male)", text, default="male", dtype=str).lower() == "male" else 0,
        "cp": extract_value(r"chest pain type.*?([\w\s]+)", text, default="Typical Angina", dtype=str),
        "trestbps": extract_value(r"resting blood pressure.*?(\d{2,3})", text, default=120, dtype=int),
        "chol": extract_value(r"serum cholesterol.*?(\d{2,4})", text, default=200, dtype=int),
        "fbs": 1 if extract_value(r"fasting blood sugar.*?(\d{2,3})", text, default=100, dtype=int) > 120 else 0,
        "thalach": extract_value(r"maximum heart rate.*?(\d{2,3})", text, default=150, dtype=int),
        "restecg": extract_value(r"resting ecg.*?([\w\s]+)", text, default="Normal", dtype=str),
        "exang": 1 if extract_value(r"exercise induced angina.*?(yes)", text, default="no", dtype=str).lower() == "yes" else 0,
        "oldpeak": extract_value(r"st depression.*?([\d.]+)", text, default=1.0, dtype=float),
        "slope": extract_value(r"slope of st segment.*?([\w\s]+)", text, default="Flat", dtype=str),
        "ca": extract_value(r"number of major vessels.*?(\d+)", text, default=0, dtype=int),
        "thal": extract_value(r"thalassemia type.*?([\w\s]+)", text, default="Normal", dtype=str)
    }

    chest_pain_mapping = {"typical angina": 1, "atypical angina": 2, "non-anginal pain": 3, "asymptomatic": 4}
    restecg_mapping = {"normal": 0, "st-t wave abnormality": 1, "left ventricular hypertrophy": 2}
    slope_mapping = {"upsloping": 1, "flat": 2, "downsloping": 3}
    thal_mapping = {"normal": 1, "fixed defect": 3, "reversible defect": 2}

    data["cp"] = chest_pain_mapping.get(data["cp"].strip().lower(), 1)
    data["restecg"] = restecg_mapping.get(data["restecg"].strip().lower(), 0)
    data["slope"] = slope_mapping.get(data["slope"].strip().lower(), 2)
    data["thal"] = thal_mapping.get(data["thal"].strip().lower(), 1)

    return data


@login_required
def dashboard_view(request):
    latest_entry = PredictionHistory.objects.filter(user=request.user).order_by('-timestamp').first()

    context = {
        'latest_prediction': latest_entry.result if latest_entry else "No prediction yet",
    }
    return render(request, "prediction/dashboard.html", context)


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import HealthCheck
from .forms import HealthCheckForm
import json

@login_required
def health_check_view(request):
    user = request.user
    checks = HealthCheck.objects.filter(user=user).order_by('-date')[:7]

    # Handle form submission
    if request.method == 'POST':
        form = HealthCheckForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = user
            entry.save()
            return redirect('health_check')  
    else:
        form = HealthCheckForm()

    # Prepare data for charts
    dates = [entry.date.strftime("%b %d") for entry in checks]
    bp = [entry.bp for entry in checks]
    cholesterol = [entry.cholesterol for entry in checks]
    sugar = [entry.sugar_level for entry in checks]

    context = {
        'form': form,
        'user': user,
        'dates': json.dumps(dates),
        'bp': json.dumps(bp),
        'cholesterol': json.dumps(cholesterol),
        'sugar': json.dumps(sugar),
    }
    return render(request, 'prediction/health_check.html', context)

#---------------------------------------------------------------------------
import random

HEALTH_TIPS = [
    "Drink at least 8 glasses of water a day 💧",
    "Get 7-8 hours of sleep to recharge 🛌",
    "Stretch daily to improve flexibility 🧘‍♂️",
    "Laugh more – it’s good for your heart 😂",
    "Eat colorful veggies for a healthy gut 🥦",
    "Take a short walk every hour 🚶‍♀️",
    "Practice deep breathing to reduce stress 😮‍💨",
    "Limit screen time before bed 🌙",
    "Posture check! Sit up straight 🪑",
    "Don’t skip breakfast – fuel your day 🍳"
]




from datetime import timedelta
from django.utils import timezone

@login_required
def daily_check_view(request):
    user = request.user
    form = DailyCheckForm()

    if request.method == 'POST':
        form = DailyCheckForm(request.POST)
        if form.is_valid():
            daily_check = form.save(commit=False)
            daily_check.user = user
            daily_check.save()
            return redirect('daily_check')

    today = timezone.now().date()
    checks = DailyCheck.objects.filter(user=user, date__gte=today - timedelta(days=6)).order_by('date')

    labels = [check.date.strftime("%b %d") for check in checks]
    heart_rate_data = [check.heart_rate for check in checks]
    spo2_data = [check.spo2 for check in checks]

    # 💪 Doughnut chart data
    target = 60  # Set your daily goal (in minutes)

# ✅ Make sure you're getting the most recent entry
    if checks.exists():
        latest = checks.order_by('id').last()  # Replace 'created_at' with your timestamp field
        print("Latest exercise_minutes:", latest.exercise_minutes)

        exercise_done = min(latest.exercise_minutes, target)
        remaining = max(target - latest.exercise_minutes, 0)
    else:
        exercise_done = 0
        remaining = target

    # ✅ Calculate percent done
    percent_done = round((exercise_done / target) * 100)
    print("Calculated percent_done:", percent_done)

    # ✅ For the chart display
    exercise_data = {
        "Completed": exercise_done,
        "Remaining": remaining
    }

    extra_tips = [
        "Drink water 💧",
        "Stretch often 🧘‍♂️",
        "Walk 10 minutes 🚶",
        "Take deep breaths 🌬️",
        "Eat a fruit 🍎",
        "Take screen breaks 👀",
        "Sit with good posture 🪑",
        "Smile more 😊",
        "Limit sugar 🍬",
        "Go outside for fresh air 🌳",
        "Try 5 min meditation 🧘",
        "Add veggies to meals 🥦",
        "Avoid late-night snacks 🌙",
        "Wash your hands 🧼",
        "Do a 1-min plank 💪",
        "Skip elevator, take stairs 🏃‍♀️",
        "Laugh a little 😄",
        "Track your steps 📱",
        "Read something positive 📖",
        "Sleep on time 🛌"
    ]

    # Pick 7 random tips (no repeats)
    selected_tips = random.sample(extra_tips, 3)

    random_tip = random.choice(HEALTH_TIPS)
    context = {
        'form': form,
        'labels': json.dumps(labels),
        'heart_rate_data': json.dumps(heart_rate_data),
        'spo2_data': json.dumps(spo2_data),
        'exercise_data': json.dumps(exercise_data),
        'percent_done': percent_done,
        'health_tip': random_tip,
        'all_tips': selected_tips
    }
    return render(request, 'prediction/daily_check.html', context)

#-------------------------------------------------------------------
import csv
from django.http import HttpResponse
from .models import PredictionHistory


@login_required
def download_history(request):
    # Fetch all predictions of the logged-in user
    history = PredictionHistory.objects.filter(user=request.user).order_by('-timestamp')

    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="prediction_history.csv"'

    writer = csv.writer(response)
    writer.writerow(['Result', 'Timestamp'])

    for record in history:
        writer.writerow([record.result, record.timestamp.strftime('%Y-%m-%d %H:%M:%S')])

    return response



@login_required
def clear_history(request):
    PredictionHistory.objects.filter(user=request.user).delete()
    return redirect('predict')  # or wherever you want to redirect
#--------------------------------------------------------------------------
def recommendations_view(request):
    user = request.user
    latest_check = HealthCheck.objects.filter(user=user).order_by('-date').first()

    general_tips = [
        "Drink at least 2 liters of water daily.",
        "Exercise 30 minutes a day.",
        "Eat leafy vegetables and avoid junk food.",
        "Sleep 7-8 hours every night.",
        "Practice meditation to reduce stress."
    ]

    emergency_tips = []

    tip_of_the_day_list = [
        "🍌 Eat potassium-rich foods like bananas to help manage blood pressure.",
        "🚶‍♂️ Take a 10-minute walk after meals to aid digestion.",
        "🧘‍♀️ Practice deep breathing to reduce stress levels.",
        "💤 Go to bed at the same time every night for better sleep quality.",
        "🥦 Add fiber to your diet to support heart health.",
        "💧 Start your morning with a glass of water to boost metabolism."
    ]

    tip_of_the_day = random.choice(tip_of_the_day_list)

    if latest_check:
        if latest_check.bp > 140:
            emergency_tips.append("⚠️ Your blood pressure is high. Please reduce salt intake and consult your doctor.")
        if latest_check.cholesterol > 240:
            emergency_tips.append("⚠️ High cholesterol detected. Avoid fatty foods and schedule a health check-up.")
        if latest_check.sugar_level > 180:
            emergency_tips.append("⚠️ Elevated sugar levels. Monitor your diet and consult a diabetologist.")

    context = {
        'general_tips': general_tips,
        'emergency_tips': emergency_tips,
        "tip_of_the_day": tip_of_the_day,
    }
    return render(request, 'prediction/recommendations.html', context)

