#REQUEST RESPONSE LOGIC
from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    return HttpResponse("Informatik Projekt 2025!")

# Create your views here.
