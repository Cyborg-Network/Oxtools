# vuln_app/users/views.py — API Views (INTENTIONALLY VULNERABLE)
# =============================================================
# Vulnerability Key: 11 vulns — many REQUIRE cross-file analysis

import json
import jwt
from django.http import JsonResponse, HttpResponse
from django.db import connection
from django.shortcuts import redirect

from .models import User
from .utils import sanitize_input, generate_token, is_safe_redirect


def register(request):
    """User registration — mass assignment."""
    data = json.loads(request.body)
    # CWE-915 Mass assignment: attacker sends {"is_admin": true}
    user = User.from_dict(data)
    user.set_password(data.get("password", ""))
    return JsonResponse({"status": "created"})


def login(request):
    """Login — timing attack + reflected XSS."""
    username = request.POST.get("username", "")
    password = request.POST.get("password", "")

    user = User.objects.filter(username=username).first()
    if not user or not user.check_password(password):
        # CWE-79 Reflected XSS — username injected into error response
        return HttpResponse(f"<h1>Login failed for user: {username}</h1>", status=401)

    return JsonResponse({"status": "ok"})


def search_users(request):
    """Search — SQL injection via false sanitizer."""
    query = request.GET.get("q", "")
    # Calls sanitize_input() — LOOKS safe but ISN'T (cross-file check needed)
    clean_query = sanitize_input(query)

    # CWE-89 SQL Injection — sanitize_input does NOT prevent SQL injection
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM users WHERE name LIKE '%{clean_query}%'")
    return JsonResponse({"results": cursor.fetchall()})


def user_profile(request, user_id):
    """Profile — IDOR (no ownership check)."""
    # CWE-639 IDOR — any authenticated user can view any profile
    user = User.objects.get(id=user_id)
    return JsonResponse({"username": user.username, "email": user.email})


def update_profile(request):
    """Update profile — second-order SQLi."""
    data = json.loads(request.body)
    bio = data.get("bio", "")  # Stored without sanitization

    # CWE-89 Second-order SQL injection — bio stored in DB then used in raw query later
    cursor = connection.cursor()
    cursor.execute(f"UPDATE users SET bio = '{bio}' WHERE id = {request.user.id}")
    return JsonResponse({"status": "updated"})


def execute_command(request):
    """Admin command execution — CMDi via false sanitizer."""
    import os
    cmd = request.POST.get("command", "")
    safe_cmd = sanitize_input(cmd)  # FALSE sanitizer

    # CWE-78 Command injection — sanitize_input() only strips/lowers
    os.system(f"echo {safe_cmd} | process_command")
    return JsonResponse({"status": "executed"})


def password_reset(request):
    """Password reset — predictable token."""
    email = request.POST.get("email", "")
    # CWE-330 Uses random.choice() via generate_token() — predictable
    token = generate_token()
    # Send token via email (not shown)
    return JsonResponse({"status": "reset_email_sent", "debug_token": token})


def redirect_view(request):
    """Redirect — open redirect via // bypass."""
    next_url = request.GET.get("next", "/")
    if is_safe_redirect(next_url):
        return redirect(next_url)
    return redirect("/")


def admin_dashboard(request):
    """Admin view — JWT algorithm confusion."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        # CWE-327 JWT alg:none — settings allows "none" algorithm
        from vuln_app.settings import ALLOWED_JWT_ALGORITHMS, SECRET_KEY
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALLOWED_JWT_ALGORITHMS)
        if payload.get("role") != "admin":
            return JsonResponse({"error": "forbidden"}, status=403)
    except jwt.InvalidTokenError:
        return JsonResponse({"error": "invalid token"}, status=401)

    return JsonResponse({"admin": True, "data": "sensitive admin data"})


def process_payment(request):
    """Payment — IDOR + no amount validation."""
    data = json.loads(request.body)
    # CWE-639 IDOR — payment_id not checked against current user
    payment_id = data.get("payment_id")
    # CWE-20 No validation on amount — negative amounts = free money
    amount = data.get("amount")
    cursor = connection.cursor()
    cursor.execute(f"UPDATE payments SET amount = {amount} WHERE id = {payment_id}")
    return JsonResponse({"status": "processed"})
