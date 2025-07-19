from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Appointment, Service
from patient.models import Patient
from branches.models import Branch
from django.utils import timezone

# Actual appointment creation logic

def create_appointment(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        branch_id = request.POST.get('branch')
        appoint_date = request.POST.get('appoint_date')
        appoint_time = request.POST.get('appoint_time')
        service_id = request.POST.get('service')
        notes = request.POST.get('notes')

        # Split full name into first and last name
        if full_name:
            parts = full_name.strip().split(' ', 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ''
        else:
            first_name = last_name = ''

        # Get or create patient by email
        patient, created = Patient.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'branch_id': branch_id,
            }
        )
        # If patient exists, update phone and names if changed
        if not created:
            updated = False
            if patient.first_name != first_name:
                patient.first_name = first_name
                updated = True
            if patient.last_name != last_name:
                patient.last_name = last_name
                updated = True
            if patient.phone != phone:
                patient.phone = phone
                updated = True
            if patient.branch_id != int(branch_id):
                patient.branch_id = branch_id
                updated = True
            if updated:
                patient.save()

        # Get branch and service
        branch = Branch.objects.get(id=branch_id)
        service = Service.objects.get(id=service_id)

        # Combine date and time
        from datetime import datetime
        date_time = datetime.strptime(f"{appoint_date} {appoint_time}", "%Y-%m-%d %H:%M")

        # Create appointment
        Appointment.objects.create(
            patient=patient,
            dentist=None,  # Not selected in form
            date_time=date_time,
            status='Pending',
            notes=notes,
            service=service,
            phone=phone,
            is_patient_new=created,
            branch=branch
        )
        request.session['appointment_created'] = True
        return redirect('index')
    return redirect('index')

@csrf_exempt
def clear_appointment_created_flag(request):
    if request.method == 'POST':
        request.session.pop('appointment_created', None)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'invalid'}, status=400)
