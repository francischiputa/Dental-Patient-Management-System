from django.utils.html import escape
from xhtml2pdf import pisa 
from django.contrib.auth import authenticate, login
from decimal import Decimal
import datetime
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.db.models import Q
from patient.models import Patient
from appointment.models import Appointment, Service, Treatment, Diagnosis
from django.contrib import messages
from user_accounts.forms import CustomUserCreationForm, DentistForm, StaffForm
from user_accounts.models import CustomUser, Dentist, Staff
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse, Http404, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.contrib.auth.models import BaseUserManager
from weasyprint import HTML
from django.contrib.auth.forms import UserCreationForm
import traceback
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from user_accounts.forms import CustomUserCreationForm
from django.contrib.auth import logout
from payments.models import Payment, Invoice
from django.db import transaction, IntegrityError
from django.contrib.auth.decorators import login_required, user_passes_test
from payments.models import Invoice, Payment, InvoiceService, Quotation, QuotationService
from payments.forms import InvoiceForm, PaymentForm
from branches.models import Branch 




def app_login(request):
    return render(request, 'login.html')

def is_admin(user):
    return user.user_type == 1

# Admin Dashboard with Branches
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    users = CustomUser.objects.all()
    branches = Branch.objects.all()  # Fetch all branches
    return render(request, 'admin_dashboard.html', {'users': users, 'branches': branches})

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        # Set default user_type for superuser (e.g., 1 for Admin)
        extra_fields.setdefault('user_type', 1)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)


def create_admin(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = 1  # Set the user type to Admin (assuming 1 corresponds to Admin)
            user.save()
            messages.success(request, "Admin account created successfully!")
            return redirect('admin_dashboard')  # Redirect to the admin dashboard or another URL
    else:
        form = CustomUserCreationForm()
    return render(request, 'create_admin.html', {'form': form})


# Create a new user with branch assignment
@login_required
@user_passes_test(is_admin)
def create_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.branch = form.cleaned_data.get('branch')  # Assign branch from form
            user.save()
            messages.success(request, f'Account created for {user.username}!')
            return redirect('admin_dashboard')
    else:
        form = CustomUserCreationForm()
    branches = Branch.objects.all()  # Pass branches to the form
    return render(request, 'create_user.html', {'form': form, 'branches': branches})



def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember')  # Get remember me value
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Set session expiry
            if not remember_me:
                # Session will expire when browser closes
                request.session.set_expiry(0)
            
            # Redirect based on user type
            if user.user_type == 1:
                return redirect('dashboard')
            elif user.user_type == 2:
                return redirect('dashboard')
            elif user.user_type == 3:
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
            return redirect('login')
    
    # If GET request or failed login, show login page
    return render(request, 'login.html')  # Make sure this matches your template name




def logout_view(request):
    logout(request)  # Logs the user out
    return redirect('login')


# Dentists Page with Branch Filter
@login_required
def DentistsPage(request):
    dentists = Dentist.objects.select_related('user__branch').all()  # Include branch in query
    branches = Branch.objects.all()
    return render(request, 'dentists.html', {'dentists': dentists, 'branches': branches})

@login_required
def Dashboard(request):
    logined_user = request.user.username

    # Total appointments
    total_appointments = Appointment.objects.all().count()

    # Total patients (using corrected query)
    total_patients = Patient.objects.count()  # Or use a valid field like role='patient' if applicable

    # Scheduled appointments
    scheduled_appointments = Appointment.objects.filter(status='Scheduled')

    # Pending appointments
    pending_appointments = Appointment.objects.filter(status='Pending')

    # Completed appointments
    completed_appointments = Appointment.objects.filter(status='Completed')

    # Cancelled appointments
    cancelled_appointments = Appointment.objects.filter(status='Cancelled')

    # Total quotations
    total_quotations = Quotation.objects.all().count()

    return render(
        request,
        'dashboard.html',
        {
            'scheduled_appointments': scheduled_appointments,
            'pending_appointments': pending_appointments,
            'completed_appointments': completed_appointments,
            'cancelled_appointments': cancelled_appointments,
            'logined_user': logined_user,
            'total_appointments': total_appointments,
            'total_patients': total_patients,
            'total_quotations': total_quotations,
        }
    )


# Patients Page with Branch Filter
@login_required
def PatientsPage(request):
    # Get the logged-in user and their branch (if any)
    user_branch = getattr(request.user, 'branch', None)

    # Fetch all branches for filtering (only for admin users)
    branches = Branch.objects.all() if request.user.user_type == 1 else None

    # Admin-specific branch filtering
    selected_branch_id = request.GET.get('branch') if request.user.user_type == 1 else None

    # Filter data based on the user's branch
    if user_branch and request.user.user_type != 1:  # Non-admin users see only their branch's data
        patients = Patient.objects.filter(branch=user_branch, is_patient=True).order_by('-id')
    else:
        # Admin users see data for all branches or the selected branch
        patients = Patient.objects.filter(is_patient=True).order_by('-id')

        if selected_branch_id:
            try:
                selected_branch = Branch.objects.get(id=selected_branch_id)
                patients = Patient.objects.filter(branch=selected_branch, is_patient=True).order_by('-id')
            except Branch.DoesNotExist:
                messages.warning(request, "Invalid branch selected. Showing all data.")

    return render(request, 'patients.html', {
        'patients': patients,
        'branches': branches,
        'selected_branch_id': selected_branch_id,
    })

# Create Patient with Branch Assignment
@login_required
def CreatePatient(request):
    if request.method == 'POST':
        first_name = request.POST.get('first-name', '').strip()
        last_name = request.POST.get('last-name', '').strip()
        date_of_birth = request.POST.get('dob', '').strip()
        gender = request.POST.get('gender', '').strip()
        nrc = request.POST.get('nrc', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        medical_history = request.POST.get('medical_history', '').strip()
        branch_id = request.POST.get('branch')  # Get branch ID from form
        if not all([first_name, last_name, date_of_birth, gender, nrc, phone]):
            messages.error(request, 'All required fields must be filled.')
            return render(request, 'create_patient.html')
        try:
            branch = Branch.objects.get(id=branch_id) if branch_id else None  # Fetch branch
            Patient.objects.create(
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                gender=gender,
                nrc=nrc,
                phone=phone,
                email=email,
                address=address,
                medical_history=medical_history,
                is_patient=True,
                branch=branch  # Assign branch to patient
            )
            messages.success(request, 'Patient created successfully!')
            return redirect('patients')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return render(request, 'create_patient.html')
    branches = Branch.objects.all()  # Pass branches to the form
    return render(request, 'create_patient.html', {'branches': branches})
@login_required
def AppointmentsPage(request):
    # Get the logged-in user and their branch (if any)
    user_branch = getattr(request.user, 'branch', None)
    
    # Debug: Print the type and value of user_branch
    print(f"DEBUG: user_branch type: {type(user_branch)}, value: {user_branch}")
    
    # Log a warning if the branch is missing or invalid
    if request.user.user_type in [2, 3] and not user_branch:
        messages.warning(request, "Your account is not assigned to a branch. Please contact the administrator.")
    
    # Fetch all branches for filtering (only for admin users)
    branches = Branch.objects.all() if request.user.user_type == 1 else None
    
    # Handle user_branch properly - convert string to Branch instance if needed
    branch_instance = None
    if user_branch:
        if isinstance(user_branch, Branch):
            branch_instance = user_branch
            print(f"DEBUG: Using existing Branch instance: {branch_instance}")
        else:
            print(f"DEBUG: user_branch is not a Branch instance, it's: {type(user_branch)}")
            # Handle case where user_branch is a string (likely the __str__ representation)
            try:
                # Try to parse "RhodesPark - Lusaka" format
                if " - " in str(user_branch):
                    name_part = str(user_branch).split(" - ")[0]
                    location_part = str(user_branch).split(" - ")[1]
                    branch_instance = Branch.objects.get(name=name_part, location=location_part)
                else:
                    # Try to find by name only
                    branch_instance = Branch.objects.get(name=str(user_branch))
                print(f"DEBUG: Found branch_instance: {branch_instance}")
            except Branch.DoesNotExist:
                print(f"DEBUG: Could not find branch for: {user_branch}")
                messages.warning(request, f"Branch '{user_branch}' not found. Please contact administrator.")
            except Branch.MultipleObjectsReturned:
                # If multiple branches match, get the first one
                if " - " in str(user_branch):
                    name_part = str(user_branch).split(" - ")[0]
                    location_part = str(user_branch).split(" - ")[1]
                    branch_instance = Branch.objects.filter(name=name_part, location=location_part).first()
                else:
                    branch_instance = Branch.objects.filter(name=str(user_branch)).first()
                print(f"DEBUG: Multiple branches found, using first: {branch_instance}")
    
    # Fetch dentists based on the branch instance
    if branch_instance:
        print(f"DEBUG: branch_instance type: {type(branch_instance)}, value: {branch_instance}")
        print(f"DEBUG: branch_instance.id: {branch_instance.id}")
        # Try filtering by branch ID instead of the instance
        try:
            dentists = Dentist.objects.filter(user__branch_id=branch_instance.id)
            print(f"DEBUG: Successfully filtered dentists by branch_id: {branch_instance.id}")
        except Exception as e:
            print(f"DEBUG: Error filtering dentists: {e}")
            dentists = Dentist.objects.all()
    else:
        print("DEBUG: No branch_instance, showing all dentists")
        dentists = Dentist.objects.all()
    
    # Admin-specific branch filtering
    selected_branch_id = request.GET.get('branch') if request.user.user_type == 1 else None
    
    # Filter data based on the user's branch
    if branch_instance and request.user.user_type != 1:  # Non-admin users see only their branch's data
        pending_appointments = Appointment.objects.filter(patient__branch=branch_instance, status='Pending')
        scheduled_appointments = Appointment.objects.filter(patient__branch=branch_instance, status='Scheduled')
        completed_appointments = Appointment.objects.filter(patient__branch=branch_instance, status='Completed')
    else:
        # Admin users see data for all branches or the selected branch
        pending_appointments = Appointment.objects.filter(status='Pending')
        scheduled_appointments = Appointment.objects.filter(status='Scheduled')
        completed_appointments = Appointment.objects.filter(status='Completed')
        
        if selected_branch_id:
            try:
                selected_branch = Branch.objects.get(id=selected_branch_id)
                pending_appointments = Appointment.objects.filter(patient__branch=selected_branch, status='Pending')
                scheduled_appointments = Appointment.objects.filter(patient__branch=selected_branch, status='Scheduled')
                completed_appointments = Appointment.objects.filter(patient__branch=selected_branch, status='Completed')
            except Branch.DoesNotExist:
                messages.warning(request, "Invalid branch selected. Showing all data.")
    
    return render(request, 'appointments.html', {
        'pending_appointments': pending_appointments,
        'scheduled_appointments': scheduled_appointments,
        'completed_appointments': completed_appointments,
        'branches': branches,
        'selected_branch_id': selected_branch_id,
        'dentists': dentists,
    })

def index(request):
    try:
        # Retrieve all branches
        branches = Branch.objects.all()
        
        # Retrieve services with valid name and price
        services = Service.objects.filter(name__isnull=False, price__isnull=False)
        
        # Debugging: Log retrieved data
        print("[DEBUG] Retrieved Branches:", [(b.id, b.name) for b in branches])
        print("[DEBUG] Retrieved Services:", [(s.id, s.name, s.price) for s in services])

        # Warn if no branches or services are available
        if not branches.exists():
            messages.warning(request, "No branches available. Please contact the administrator.")
        if not services.exists():
            messages.warning(request, "No services available. Please contact the administrator.")

    except Exception as e:
        # Catch unexpected errors and log them
        print(f"[ERROR] An error occurred while fetching branches or services: {str(e)}")
        messages.error(request, "An error occurred while loading the page. Please try again later.")
        branches = []
        services = []

    # Pass data to the template
    return render(request, 'index.html', {
        'branches': branches,
        'services': services,
    })


@csrf_exempt
def clear_appointment_created_flag(request):
    if request.method == 'POST':
        request.session.pop('appointment_created', None)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'}, status=400)




def create_appointment(request):
    if request.method == 'POST':
        try:
            # Retrieve form data
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            appoint_date = request.POST.get('appoint_date')
            appoint_time = request.POST.get('appoint_time')
            service_id = request.POST.get('service')
            branch_id = request.POST.get('branch')  # Get the selected branch
            notes = request.POST.get('notes')

            # Validate full name
            if ' ' not in full_name:
                messages.error(request, "Full name must include both first and last names.")
                return redirect('index')

            first_name, last_name = full_name.rsplit(' ', 1)

            # Validate service selection
            try:
                service = Service.objects.get(id=service_id)
            except Service.DoesNotExist:
                messages.error(request, "Invalid service selected.")
                return redirect('index')

            # Validate branch selection
            try:
                branch = Branch.objects.get(id=branch_id)
            except Branch.DoesNotExist:
                messages.error(request, "Invalid branch selected.")
                return redirect('index')

            # Parse and validate date and time
            try:
                date_time_str = f"{appoint_date} {appoint_time}"
                naive_date_time = timezone.datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
                aware_date_time = timezone.make_aware(naive_date_time, timezone.get_default_timezone())
            except ValueError:
                messages.error(request, "Invalid date or time format. Please use YYYY-MM-DD HH:MM.")
                return redirect('index')

            # Create or retrieve the patient
            patient, created = Patient.objects.get_or_create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                defaults={'phone': phone, 'branch': branch}
            )

            # Create the appointment
            appointment = Appointment.objects.create(
                patient=patient,
                date_time=aware_date_time,
                service=service,
                notes=notes
            )

            # Notify via Channels (if applicable)
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    "appointment_notifications",
                    {
                        "type": "send_notification",
                        "message": (
                            f"New appointment: {appointment.patient.first_name} {appointment.patient.last_name}, "
                            f"Service: {appointment.service.name}, "
                            f"Date: {appointment.date_time.strftime('%Y-%m-%d %H:%M')}"
                        )
                    }
                )

            # Set success message and redirect
            messages.success(request, "Appointment created successfully!")
            return redirect('index')

        except Exception as e:
            # Catch unexpected errors and log them
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('index')

    # Handle GET requests
    return render(request, 'index.html')


@csrf_protect
def walk_in_appointment(request):
    if request.method == 'POST':
        try:
            # Retrieve form data
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            appoint_date = request.POST.get('appoint_date')
            appoint_time = request.POST.get('appoint_time')
            service_id = request.POST.get('service')
            notes = request.POST.get('notes')

            # Validate full name
            if ' ' not in full_name:
                messages.error(request, "Full name must include both first and last names.")
                return redirect('scheduled_appointment')

            first_name, last_name = full_name.rsplit(' ', 1)

            # Validate service selection
            try:
                service = Service.objects.get(id=service_id)
            except ObjectDoesNotExist:
                messages.error(request, "Invalid service selected.")
                return redirect('scheduled_appointment')

            # Ensure a dentist is available
            dentist = Dentist.objects.first()
            if not dentist:
                messages.error(request, "No dentists available to assign appointments.")
                return redirect('scheduled_appointment')

            # Parse and validate date and time
            try:
                date_time_str = f"{appoint_date} {appoint_time}"
                naive_date_time = timezone.datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
                aware_date_time = timezone.make_aware(naive_date_time, timezone.get_default_timezone())
            except ValueError:
                messages.error(request, "Invalid date or time format. Please use YYYY-MM-DD HH:MM.")
                return redirect('scheduled_appointment')

            # Create or retrieve the patient
            try:
                patient, created = Patient.objects.get_or_create(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    defaults={'phone': phone}
                )
            except Exception as e:
                messages.error(request, f"Error creating or retrieving patient: {str(e)}")
                return redirect('scheduled_appointment')

            # Create the appointment
            appointment = Appointment.objects.create(
                patient=patient,
                dentist=dentist,
                date_time=aware_date_time,
                service=service,
                notes=notes
            )

            # Notify via Channels
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    "appointment_notifications",
                    {
                        "type": "send_notification",
                        "message": (
                            f"New appointment: {appointment.patient.first_name} {appointment.patient.last_name}, "
                            f"Service: {appointment.service.name}, "
                            f"Date: {appointment.date_time.strftime('%Y-%m-%d %H:%M')}"
                        )
                    }
                )

            # Set session flag and redirect
            request.session['appointment_created'] = True
            messages.success(request, "Appointment created successfully!")
            return redirect('scheduled_appointment')

        except Exception as e:
            # Catch unexpected errors and log them
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return redirect('scheduled_appointment')

    # Handle GET requests
    return render(request, 'scheduled_appointment.html')



def patient_details(request, id):
    patient = get_object_or_404(Patient, id=id)
    appointments = Appointment.objects.filter(patient=patient)
    treatments = Treatment.objects.filter(appointment__in=appointments)
    diagnoses = Diagnosis.objects.filter(appointment__in=appointments)
    
    context = {
        'patient': patient,
        'appointments': appointments,
        'treatments': treatments,
        'diagnoses': diagnoses,
    }
    return render(request, 'patient_details.html', context)


@login_required
def assign_dentist(request):
    if request.method == 'POST':
        appointment_id = request.POST.get('appointmentId')
        dentist_id = request.POST.get('dentist')

        if not appointment_id or not dentist_id:
            return JsonResponse({'success': False, 'message': 'Missing appointment or dentist ID.'})

        try:
            appointment = Appointment.objects.get(id=appointment_id)
            dentist = Dentist.objects.get(id=dentist_id)
        except (Appointment.DoesNotExist, Dentist.DoesNotExist):
            return JsonResponse({'success': False, 'message': 'Invalid appointment or dentist ID.'})

        # Assign dentist and set status to 'Scheduled'
        appointment.dentist = dentist
        appointment.status = 'Scheduled'

        try:
            appointment.save()  # Save the changes to the database
        except Exception as e:
            print(f'Error saving appointment: {e}')
            return JsonResponse({'success': False, 'message': f'Error saving appointment: {e}'})

        return JsonResponse({'success': True, 'message': 'Dentist assigned successfully.'})
    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})
    

@login_required
def scheduled_appointment_view(request):
    appointments = Appointment.objects.all()
    services = Service.objects.all()
    services = Service.objects.all()
    return render(request, 'schuled_appointment.html', {'appointments':appointments, 'services':services})


def treatment_request(request, patient_id):
    try:
        # Fetch the patient object or raise 404 if not found
        patient = get_object_or_404(Patient, id=patient_id)
    except Exception as e:
        print(f"Error fetching patient: {e}")
        raise Http404("Patient not found")

   
    try:
        # Fetch services object or raise 404 if not found
        services = Service.objects.filter(name__isnull=False, price__isnull=False).order_by('name')
        print(f"List of services: {[(s.id, s.name, s.price) for s in services]}")  # Debug statement
    except Exception as e:
        print(f"Error fetching services: {e}")
        services = []  # Fallback to an empty list if an error occurs

    if not services:
        print("[WARNING] No services found matching the filter criteria.")
        messages.warning(request, "No services available. Please contact the administrator.")

    # Pass the patient object and services to the template for display
    context = {
        'patient': patient,
        'services': services,
    }
    return render(request, 'treatment_request.html', context)

@login_required
def treatment_diagnosis(request):
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        service_id = request.POST.get('services')
        treatment_text = request.POST.get('treatment_text')
        diagnosis_text = request.POST.get('diagnosis_text')
        date_str = request.POST.get('date')

        # Check required fields
        if not all([patient_id, service_id, treatment_text, diagnosis_text, date_str]):
            messages.error(request, 'Missing required fields.')
            return render(request, 'patients.html')

        # Validate date
        try:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format. Use YYYY-MM-DD.')
            return render(request, 'patients.html')

        # Get patient
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            messages.error(request, 'Patient not found.')
            return render(request, 'patients.html')
# Check appointments
        appointments = Appointment.objects.filter(patient=patient, status='Scheduled')
        if not appointments.exists():
            messages.error(request, 'No scheduled appointments found. Create one first.')
            return render(request, 'patients.html')
        appointment = appointments.first()

        # Get service
        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            messages.error(request, 'Service not found.')
            return render(request, 'patients.html')

        # Create records
        try:
            Treatment.objects.create(
                appointment=appointment,
                service=service,
                treatment_text=treatment_text,
                date=date
            )
            Diagnosis.objects.create(
                appointment=appointment,
                service=service,
                diagnosis_text=diagnosis_text,
                date=date
            )
        except Exception as e:
            messages.error(request, f'Error saving data: {str(e)}')
            return render(request, 'patient.html')

        messages.success(request, 'Treatment and diagnosis saved successfully.')
        return render(request, 'patients.html')
    else:
        return render(request, 'patients.html')

        

def update_patient_request(request, patient_id):
    patient = Patient.objects.get(id=patient_id)
    return render(request, 'patient_update.html', {'patient': patient})

def update_patient(request):
    if request.method == 'POST':
        # Retrieve form data from the POST request
        patient_id = request.POST.get('patient_id')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        nrc = request.POST.get('nrc')
        gender = request.POST.get('gender')
        date_of_birth = request.POST.get('dob')
        address = request.POST.get('address')

        try:
            # Attempt to fetch the patient by ID
            patient = get_object_or_404(Patient, id=patient_id)

            # Update patient fields
            patient.first_name = first_name
            patient.last_name = last_name
            patient.date_of_birth = date_of_birth
            patient.email = email
            patient.phone = phone
            patient.nrc = nrc
            patient.gender = gender
            patient.address = address
            patient.is_patient = True  # Assuming this field exists in your model

            # Save the updated patient
            patient.save()

            # Add success message
            messages.success(request, 'Patient updated successfully!')
        except Patient.DoesNotExist:
            # Handle the case where the patient does not exist
            messages.error(request, 'Failed to update the patient. The patient does not exist.')

        # Redirect to the patients page
        return redirect('patients')

    else:
        # If the request method is not POST, show an error message
        messages.error(request, 'Failed to update the patient. Make sure all required fields are filled.')
        return redirect('patients')

# Search Patient with Branch Filter
@login_required
def search_patient(request):
    if request.method == 'POST':
        search_query = request.POST.get('search_services', '').strip()
        branch_id = request.POST.get('branch')  # Get branch ID from form
        query = Q()
        if search_query:
            query |= Q(first_name__icontains=search_query)
            query |= Q(last_name__icontains=search_query)
            query |= Q(email__icontains=search_query)
            query |= Q(nrc__icontains=search_query)
        patients = Patient.objects.filter(query)
        if branch_id:
            patients = patients.filter(branch_id=branch_id)  # Filter by branch
        branches = Branch.objects.all()
        return render(request, 'search_patient.html', {'patients': patients, 'branches': branches})
    branches = Branch.objects.all()
    return render(request, 'search_patient.html', {'branches': branches})

def complete_appointment(request, appointment_id):
    try:
        # Attempt to fetch the appointment by ID
        appointment = get_object_or_404(Appointment, id=appointment_id)

        # Fetch the associated patient
        patient = appointment.patient
        print(f"Received appointment_id: {appointment_id}")

        # Mark the appointment as completed
        appointment.status = 'Completed'
        appointment.save()
        print('completed')

        # Add success message
        messages.success(request, 'Appointment Completed.')

    except Appointment.DoesNotExist:
        # Handle the case where the appointment does not exist
        messages.error(request, 'Appointment not found.')

    # Redirect to the dashboard
    return redirect('appointments')


#  Helper decorator for staff check
def staff_required(view_func):
    decorated_view = login_required(user_passes_test(lambda u: u.is_staff)(view_func))
    return decorated_view

def invoice_list_view(request):
    invoices = Invoice.objects.all()
    return render(request, 'invoice_list.html', {
        'invoices': invoices
    })



@staff_required
def invoice_detail_view(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if request.method == 'POST':
        # Handle payment form submission
        payment_form = PaymentForm(request.POST, invoice=invoice)
        if payment_form.is_valid():
            payment = payment_form.save(commit=False)
            payment.invoice = invoice
            payment.patient = invoice.patient
            payment.processed_by = request.user
            payment.save()
            return redirect('invoice_detail', pk=pk)
    else:
        payment_form = PaymentForm(invoice=invoice)
    
    payments = invoice.payment_set.all()
    remaining_balance = invoice.get_remaining_balance()
    
    return render(request, 'invoice_detail.html', {
        'object': invoice,
        'payment_form': payment_form,
        'payments': payments,
        'remaining_balance': remaining_balance
    })


def create_payment(request, invoice_id):
    try:
        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
            
            # Get form data
            amount = request.POST.get('amount')
            payment_method = request.POST.get('payment_method')
            transaction_id = request.POST.get('transaction_id', '')
            notes = request.POST.get('notes', '')

            # Validate required fields
            if not all([amount, payment_method]):
                return JsonResponse({'error': 'Missing required fields'}, status=400)

            # Convert amount to decimal
            try:
                amount = Decimal(amount)
            except:
                return JsonResponse({'error': 'Invalid amount format'}, status=400)

            # Check if payment exceeds remaining balance
            remaining_balance = invoice.total_amount - invoice.get_total_payments()
            if amount > remaining_balance:
                return JsonResponse({
                    'error': f'Payment exceeds remaining balance of {remaining_balance:.2f}'
                }, status=400)

            # Create payment instance
            payment = Payment(
                patient=invoice.patient,
                invoice=invoice,
                appointment=invoice.appointment,
                processed_by=request.user,
                amount=amount,
                payment_method=payment_method,
                transaction_id=transaction_id if payment_method != 'cash' else '',
                notes=notes,
                status='completed'  # Assuming immediate completion for cash payments
            )

            # Validate and save
            payment.full_clean()
            payment.save()

            # Return success response
            return JsonResponse({
                'status': 'success',
                'payment_id': payment.id,
                'invoice_status': invoice.status,
                'remaining_balance': float(invoice.total_amount - invoice.get_total_payments())
            })

    except Invoice.DoesNotExist:
        return JsonResponse({'error': 'Invoice not found'}, status=404)
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Payment failed: ' + str(e)}, status=500)




# Create invoice template
def create_invoice_list_view(request):
    patients = Patient.objects.filter(is_patient=True)
    return render(request, 'create_invoice.html', {
        'patients': patients
    })

def create_invoice(request):
    if request.method == 'POST':
    # Retrieve the patient ID from the request (e.g., via query parameters or POST data)
        patient_id = request.GET.get('patient_id') or request.POST.get('patient_id')
        if not patient_id:
            return HttpResponseBadRequest("Patient ID is required.")

        # Fetch the patient object
        patient = get_object_or_404(Patient, id=patient_id)

    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Create the invoice
                invoice = form.save(commit=False)
                invoice.created_by = request.user
                invoice.patient = patient  # Associate the invoice with the patient
                invoice.save()

                # Process selected services
                selected_service_ids = request.POST.getlist('services')  # Get selected service IDs
                total_amount = 0

                for service_id in selected_service_ids:
                    service = get_object_or_404(Service, id=service_id)
                    InvoiceService.objects.create(
                        invoice=invoice,
                        service=service,
                        price_at_time=service.price
                    )
                    total_amount += service.price  # Accumulate the total amount

                # Update the invoice's total amount
                invoice.total_amount = total_amount
                invoice.save()

                # Redirect to the invoice list or detail page
                return redirect('invoice_list')
    else:
        # Pre-fill the form with patient details
        initial_data = {
            'patient_id': patient.id,
            'email': patient.email,
            'phone': patient.phone,
        }
        form = InvoiceForm(initial=initial_data)

    # Fetch all available services for the dropdown
    services = Service.objects.all()
    # message for error
    messages.error(request, 'An error occurred. Please try again.')

    return render(request, 'invoice_form.html', {
        'form': form,
        'patient': patient,
        'services': services,
        'messages': messages  # Get the error message from the session
    })

    
def patient_invoice(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    services = Service.objects.all()
    return render(request, 'invoice_form.html', {
        'patient': patient,
        'services': services
    })


def create_quotation_list(request):
    patients = Patient.objects.all()
    return render(request, 'create_quotation_list.html', {
        'patients': patients
    })




def create_quotation(request):
    if request.method == 'POST':
        # Retrieve form data
        patient_id = request.POST.get('patient_id')
        selected_service_ids = request.POST.getlist('services')
        quantities = request.POST.getlist('quantities')

        # Validate inputs
        if not selected_service_ids:
            return JsonResponse({'error': 'No services selected'}, status=400)

        if len(quantities) < len(selected_service_ids):
            return JsonResponse({'error': 'Missing quantities for some services'}, status=400)

        # Fetch the patient object
        patient = get_object_or_404(Patient, id=patient_id)

        # Branch logic: Ensure the patient has a branch assigned
        if not patient.branch:
            return JsonResponse({'error': 'The selected patient does not belong to any branch.'}, status=400)

        # Optional: Restrict to the logged-in user's branch (if applicable)
        if hasattr(request.user, 'branch') and request.user.branch != patient.branch:
            return JsonResponse({'error': 'You can only create quotations for patients in your branch.'}, status=403)

        with transaction.atomic():
            # Create the quotation
            quotation = Quotation.objects.create(
                patient=patient,
                status='draft',
                branch=patient.branch  # Assign the patient's branch to the quotation
            )

            # Add selected services to the quotation
            total_amount = Decimal('0.00')
            for i, service_id in enumerate(selected_service_ids):
                service = get_object_or_404(Service, id=service_id)

                # Ensure quantity exists before accessing
                try:
                    quantity = int(quantities[i])
                except (IndexError, ValueError):
                    quantity = 1  # Default quantity if missing or invalid

                price_at_time = service.price  # Capture the current price
                total_amount += price_at_time * quantity

                # Create QuotationService records
                QuotationService.objects.create(
                    quotation=quotation,
                    service=service,
                    price_at_time=price_at_time,
                    quantity=quantity
                )

            # Update the total amount
            quotation.total_amount = total_amount
            quotation.save()

            return redirect('quotation_detail', pk=quotation.pk)

    # Fetch all patients and services for the form
    patients = Patient.objects.all()
    services = Service.objects.all()

    # Pass branch information for filtering (optional)
    branches = set(Patient.objects.values_list('branch__id', 'branch__name').distinct())

    return render(request, 'create_quotation.html', {
        'patients': patients,
        'services': services,
        'branches': branches  # Pass branches to the template for filtering
    })


def quotation_detail(request, pk):
    # Fetch the quotation object
    quotation = get_object_or_404(Quotation, pk=pk)

    # Include branch information in the context
    branch_name = quotation.branch.name if quotation.branch else "No Branch Assigned"
    branch_address = quotation.branch.address if quotation.branch else "N/A"

    return render(request, 'quotation_detail.html', {
        'quotation': quotation,
        'branch_name': branch_name,
        'branch_address': branch_address
    })


def download_quotation_pdf(request, quotation_id):
    """
    Generate and download a quotation PDF that matches the provided image design.
    Includes branch information for the patient.
    """
    # Fetch the quotation object
    quotation = get_object_or_404(Quotation, id=quotation_id)

    # Get the patient's branch information
    patient_branch_name = quotation.patient.branch.name if quotation.patient.branch else "No Branch Assigned"
    patient_branch_address = quotation.patient.branch.address if quotation.patient.branch else "N/A"

    # Build the HTML content for the PDF
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 40px; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; }}
            .header img {{ width: 100px; }}
            .quotation-title {{ background-color: #00A9CE; color: white; font-size: 24px; padding: 10px; text-align: center; font-weight: bold; }}
            .details {{ display: flex; justify-content: space-between; margin-top: 20px; }}
            .details div {{ width: 45%; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ccc; padding: 10px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .total-section {{ text-align: right; margin-top: 20px; }}
            .total-section p {{ margin: 5px 0; }}
            .grand-total {{ background-color: #00A9CE; color: white; padding: 10px; font-size: 18px; font-weight: bold; text-align: right; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h2> Superior Dental Solutions Limited</h2>
                <p><strong>Branch:</strong> {escape(patient_branch_name)}</p>
                <p><strong>Address:</strong> {escape(patient_branch_address)}</p>
            </div>
            <div>
                <div>
                    <p>Valid till: {quotation.valid_until.strftime('%Y-%m-%d') if quotation.valid_until else 'Not specified'}</p>
                    <p>Total: K{quotation.total_amount:.2f}</p>
                </div>
            </div>
        </div>
        <div class="quotation-title">QUOTATION</div>
        <div class="details">
            <div>
                <strong>Quote from:</strong>
                <p>Superior Dental Solution Limited </p>
                <p>{escape(patient_branch_address)}</p>
                <p>Phone Number</p>
            </div>
            <div>
                <strong>Quote to:</strong>
                <p>{escape(quotation.patient.first_name)} {escape(quotation.patient.last_name)}</p>
                <p>{escape(quotation.patient.address)}</p>
                <p>{escape(quotation.patient.phone)}</p>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Service</th>
                    <th>Rate</th>
                    <th>Quantity</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
    """

    # Add services to the table
    for service in quotation.services.all():
        html_content += f"""
                <tr>
                    <td>{escape(service.name)}</td>
                    <td>K{service.price:.2f}</td>
                    <td>{service.quantity}</td>
                    <td>K{service.price * service.quantity:.2f}</td>
                </tr>
        """

    html_content += f"""
            </tbody>
        </table>
        <div class="total-section">
            <p>Subtotal: K{quotation.total_amount:.2f}</p>
            <p>Discount: K0.00</p>
            <p>Tax: K0.00</p>
        </div>
        <div class="grand-total">
            Total: K{quotation.total_amount:.2f}
        </div>
    </body>
    </html>
    """

    # Generate the PDF response
    pdf_response = HttpResponse(content_type='application/pdf')
    pdf_response['Content-Disposition'] = f'attachment; filename="Quotation_{quotation.id}.pdf"'
    HTML(string=html_content).write_pdf(pdf_response)
    return pdf_response



@login_required
def quotation_list(request):
    # Default queryset: All quotations
    quotations = Quotation.objects.all()

    # Fetch all branches for filtering (only for admin users)
    branches = Branch.objects.all() if request.user.user_type == 1 else None

    # Admin-specific branch filtering
    if request.user.user_type == 1:
        selected_branch_id = request.GET.get('branch')
        if selected_branch_id:
            try:
                selected_branch = Branch.objects.get(id=selected_branch_id)
                quotations = quotations.filter(patient__branch=selected_branch)
            except Branch.DoesNotExist:
                messages.warning(request, "Invalid branch selected. Showing all quotations.")
    else:
        selected_branch_id = None

    return render(request, 'quotation_list.html', {
        'quotations': quotations,
        'branches': branches,
        'selected_branch_id': selected_branch_id
    })


# Existing Patient Appointment with Branch Assignment
@login_required
def exist_patient_appointment(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    services = Service.objects.filter(name__isnull=False, price__isnull=False)
    branches = Branch.objects.all()
    if request.method == 'POST':
        appoint_date = request.POST.get('appoint_date')
        appoint_time = request.POST.get('appoint_time')
        service_id = request.POST.get('service')
        notes = request.POST.get('notes')
        branch_id = request.POST.get('branch')  # Get branch ID from form
        try:
            service = Service.objects.get(id=service_id)
            branch = Branch.objects.get(id=branch_id) if branch_id else None  # Fetch branch
            dentist = Dentist.objects.filter(user__branch=branch).first()  # Find dentist in the same branch
            if not dentist:
                messages.error(request, "No dentists available in the selected branch.")
                return redirect('exist_patient_appointment', patient_id=patient_id)
            date_time_str = f"{appoint_date} {appoint_time}"
            naive_date_time = timezone.datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
            aware_date_time = timezone.make_aware(naive_date_time, timezone.get_default_timezone())
            Appointment.objects.create(
                patient=patient,
                dentist=dentist,
                date_time=aware_date_time,
                service=service,
                notes=notes
            )
            messages.success(request, "Appointment created successfully!")
            return redirect('patients')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('exist_patient_appointment', patient_id=patient_id)
    return render(request, 'existing_patient_appointment.html', {'patient': patient, 'services': services, 'branches': branches})

# Existing Patient Appointment with Branch Assignment
@login_required
def exist_patient_appointment(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    services = Service.objects.filter(name__isnull=False, price__isnull=False)
    branches = Branch.objects.all()
    if request.method == 'POST':
        appoint_date = request.POST.get('appoint_date')
        appoint_time = request.POST.get('appoint_time')
        service_id = request.POST.get('service')
        notes = request.POST.get('notes')
        branch_id = request.POST.get('branch')  # Get branch ID from form
        try:
            service = Service.objects.get(id=service_id)
            branch = Branch.objects.get(id=branch_id) if branch_id else None  # Fetch branch
            dentist = Dentist.objects.filter(user__branch=branch).first()  # Find dentist in the same branch
            if not dentist:
                messages.error(request, "No dentists available in the selected branch.")
                return redirect('exist_patient_appointment', patient_id=patient_id)
            date_time_str = f"{appoint_date} {appoint_time}"
            naive_date_time = timezone.datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
            aware_date_time = timezone.make_aware(naive_date_time, timezone.get_default_timezone())
            Appointment.objects.create(
                patient=patient,
                dentist=dentist,
                date_time=aware_date_time,
                service=service,
                notes=notes
            )
            messages.success(request, "Appointment created successfully!")
            return redirect('patients')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('exist_patient_appointment', patient_id=patient_id)
    return render(request, 'existing_patient_appointment.html', {'patient': patient, 'services': services, 'branches': branches})
