#REQUEST RESPONSE LOGIC
from django.http import HttpResponse
from django.shortcuts import render


def index(request):
    return render(request, "main/index.html")

def vote(request):
    return render(request, "main/vote.html")

def results(request):
    return render(request, "main/results.html")

def login(request):
    return render(request, "main/login.html")