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
from django.http import HttpResponse
from django.utils.html import escape
from django.shortcuts import get_object_or_404
from weasyprint import HTML
from django.db.models import Sum
from django.db.models import F
import calendar
from inventory.models import InventoryItem, InventoryTransaction, Supplier, ItemCategory
from payments.models import Receipt # Import the Receipt model
from inventory.forms import TransactionForm, ItemForm, SupplierForm, CategoryForm
from django.template.loader import render_to_string
from branches.models import Branch 




def app_login(request):
    return render(request, 'login.html')

def is_admin(user):
    return user.user_type == 1

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    users = CustomUser.objects.all()
    return render(request, 'admin_dashboard.html', {'users': users})



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

def create_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')  # Redirect to the login page or another URL
    else:
        form = CustomUserCreationForm()
    return render(request, 'create_user.html', {'form': form})


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


def DentistsPage(request):
    dentists = Dentist.objects.all()
    return render(request, 'dentists.html', {'dentists': dentists})

@login_required
def Dashboard(request):
    logined_user = request.user.username
    total_appointments = Appointment.objects.all().count()
    total_patients = Patient.objects.all().count()
    scheduled_appointments = Appointment.objects.filter(status='Scheduled')
    pending_appointments = Appointment.objects.filter(status='Pending')
    completed_appointments = Appointment.objects.filter(status='Completed')
    cancelled_appointments = Appointment.objects.filter(status='Cancelled')
    total_quotations = Quotation.objects.all().count()
    return render(request, 'dashboard.html', {'scheduled_appointments': scheduled_appointments, 'pending_appointments': pending_appointments, 'completed_appointments': completed_appointments, 'cancelled_appointments': cancelled_appointments, 'logined_user': logined_user, 'total_appointments': total_appointments, 'total_patients': total_patients, 'total_appointments': total_appointments
                                              , 'total_quotations': total_quotations})
    
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

@login_required
def CreatePatient(request):
    if request.method == 'POST':
        # Retrieve form data
        first_name = request.POST.get('first-name', '').strip()
        last_name = request.POST.get('last-name', '').strip()
        date_of_birth = request.POST.get('dob', '').strip()
        gender = request.POST.get('gender', '').strip()
        nrc = request.POST.get('nrc', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        medical_history = request.POST.get('medical_history', '').strip()

        # Validate required fields
        if not all([first_name, last_name, date_of_birth, gender, nrc, phone]):
            messages.error(request, 'All required fields must be filled.')
            return render(request, 'create_patient.html')

        # Create the patient
        try:
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
                is_patient=True
            )
            messages.success(request, 'Patient created successfully!')
            return redirect('patients')  # Redirect to the patients list page
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return render(request, 'create_patient.html')

    # Render the form for GET requests
    return render(request, 'create_patient.html')



def AppointmentsPage(request):
    # Retrieve pending appointments
    pending_appointments = Appointment.objects.filter(status='Pending')
    scheduled_appointments = Appointment.objects.filter(status='Scheduled')
    completed_appointments = Appointment.objects.filter(status='Completed')
    
    # Retrieve dentists with user_type=3
    dentists = Dentist.objects.filter(user__user_type=3)
    
    # Retrieve services with valid name and price
    services = Service.objects.filter(name__isnull=False, price__isnull=False)

    # Pass all data to the template
    return render(
        request,
        'appointments.html',
        {
             'pending_appointments': pending_appointments,
            'completed_appointments': completed_appointments,   # Retrieve completed appointments
            'scheduled_appointments': scheduled_appointments,  # Retrieve scheduled appointments
            'dentists': dentists,
            'services': services,
        }
    )


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



@csrf_protect
def create_appointment(request):
    if request.method == 'POST':
        try:
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            appoint_date = request.POST.get('appoint_date')
            appoint_time = request.POST.get('appoint_time')
            service_id = request.POST.get('service')
            notes = request.POST.get('notes')

            # Handle cases where full_name does not contain a space
            if ' ' in full_name:
                first_name, last_name = full_name.rsplit(' ', 1)
            else:
                messages.error(request, "Full name must include both first and last names.")
                return redirect('index')

            # Check if the service exists
            try:
                service = Service.objects.get(id=service_id)
            except ObjectDoesNotExist:
                messages.error(request, "Invalid service selected.")
                return redirect('index')

            # Ensure a dentist is available
            dentist = Dentist.objects.first()
            if not dentist:
                messages.error(request, "No dentists available to assign appointments.")
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
                defaults={'phone': phone}
            )

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
                        "message": f"New appointment: {appointment.patient.first_name} {appointment.patient.last_name}, Service: {appointment.service.name}, Date: {appointment.date_time.strftime('%Y-%m-%d %H:%M')}"
                    }
                )

            # Set session flag and redirect
            request.session['appointment_created'] = True
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

            # Get the branch of the logged-in user or dentist
            if request.user.is_authenticated and hasattr(request.user, 'dentist'):
                branch = request.user.dentist.branch  # Assuming Dentist has a ForeignKey to Branch
            else:
                branch = None  # Default to None if no branch is found

            # Create or retrieve the patient
            try:
                patient, created = Patient.objects.get_or_create(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    defaults={
                        'phone': phone,
                        'branch': branch  # Assign the branch here
                    }
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

# Search for patient


def search_patient(request):
    if request.method == 'POST':
        # Retrieve the search input
        search_services = request.POST.get('search_services', '').strip()

        # Build a dynamic query
        query = Q()
        if search_services:
            query |= Q(first_name__icontains=search_services)
            query |= Q(last_name__icontains=search_services)
            query |= Q(email__icontains=search_services)
            query |= Q(nrc__icontains=search_services)

        # Filter patients based on the query
        if query:
            patients = Patient.objects.filter(query)
        else:
            patients = Patient.objects.none()  # Return no results if search_services is empty

        # Render the results
        return render(request, 'search_patient.html', {'patients': patients})

    else:
        # No records found
        messages.error(request, 'No records found.')
        # Render the search form again
        return render(request,'search_patient.html', {'messages': messages})


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



def turn_to_invoice(request, quotation_id):
    """
    Converts an existing Quotation into an Invoice.
    Copies all details from the Quotation to the Invoice without modifications.
    """
    # Fetch the Quotation and related QuotationService records
    quotation = get_object_or_404(Quotation, id=quotation_id)
    quotation_services = quotation.quotationservice_set.all()

    try:
        with transaction.atomic():
            # Create the Invoice object
            invoice = Invoice.objects.create(
                patient=quotation.patient,
                total_amount=quotation.total_amount,
                status='issued',  # Set the initial status as 'issued'
                branch=quotation.branch,  # Copy the branch from the Quotation
                created_by=request.user  # Associate the logged-in user as the creator
            )

            # Copy QuotationService details to InvoiceService
            for qs in quotation_services:
                InvoiceService.objects.create(
                    invoice=invoice,
                    service=qs.service,
                    quantity=qs.quantity,
                    price_at_time=qs.price_at_time
                )

            # Mark the Quotation as 'issued' (optional, if you want to track its conversion)
            quotation.status = 'issued'
            quotation.save()

    except Exception as e:
        # Handle any unexpected errors during the process
        messages.error(request, f"Failed to create the invoice: {str(e)}")
        return redirect('quotation_list')  # Redirect to the list of quotations

    # Add a success message
    messages.success(request, "The quotation has been successfully converted into an invoice.")

    # Redirect to the invoice detail page
    return redirect('invoice_list', invoice_id=invoice.id)


def patient_quotation(request, patient_id):
    """
    Display the quotation form for a specific patient.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    services = Service.objects.all()  # Fetch all available services
    return render(request, 'quotation_form.html', {
        'patient': patient,
        'services': services
    })


@login_required
def delete_quotation(request, pk):
    """
    Delete a quotation by its primary key (id).
    """
    quotation = get_object_or_404(Quotation, id=pk)

    if request.method == "POST":
        # Delete the quotation
        quotation.delete()
        messages.success(request, "Quotation deleted successfully.")
        return redirect('quotation_list')

    # Render a confirmation page or redirect back if not POST
    return redirect('quotation_list')



@login_required
def invoice_detail_view(request, invoice_id):
    # Fetch the invoice object
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    # Retrieve all services associated with the invoice
    services_with_subtotals = InvoiceService.objects.filter(invoice=invoice).annotate(
        subtotal=F('price_at_time') * F('quantity')
    )

    # Calculate remaining balance
    remaining_balance = invoice.get_remaining_balance()

    # Render the template with the context data
    return render(request, 'invoice_detail.html', {
        'invoice': invoice,
        'services_with_subtotals': services_with_subtotals,
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
    print(f"Request Method: {request.method}")  # Debugging statement

    if request.method == 'POST':
        print("Processing POST request...")  # Debugging statement

        # Retrieve form data from POST
        patient_id = request.POST.get('patient_id')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        selected_service_ids = request.POST.getlist('services')  # Get list of selected service IDs

        print(f"Patient ID: {patient_id}")  # Debugging statement
        print(f"Email: {email}")            # Debugging statement
        print(f"Phone: {phone}")            # Debugging statement
        print(f"Selected Services: {selected_service_ids}")  # Debugging statement

        # Validate required fields
        if not patient_id:
            messages.error(request, "Patient ID is required.")
            return redirect('create_invoice')

        if not selected_service_ids:
            messages.error(request, "At least one service must be selected.")
            return redirect('create_invoice')

        # Fetch the patient object
        try:
            patient = get_object_or_404(Patient, id=patient_id)
        except Exception as e:
            messages.error(request, f"Invalid Patient ID: {str(e)}")
            return redirect('create_invoice')

        # Fetch selected services
        services = Service.objects.filter(id__in=selected_service_ids)
        if not services.exists():
            messages.error(request, "No valid services found.")
            return redirect('create_invoice')

        # Calculate total amount
        total_amount = sum(service.price for service in services)

        # Create the invoice
        try:
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    patient=patient,
                    created_by=request.user,
                    total_amount=total_amount
                )

                # Link services to the invoice
                for service in services:
                    InvoiceService.objects.create(
                        invoice=invoice,
                        service=service,
                        price_at_time=service.price
                    )

                # Add success message
                messages.success(request, "Invoice created successfully!")
                return redirect('invoice_list')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('invoice_list')

    else:
        print("Processing GET request...")  # Debugging statement

        # Handle GET request
        patient_id = request.GET.get('patient_id')
        if not patient_id:
            print(patient_id)
            messages.error(request, "Patient ID is required.")
            return redirect('invoice_list')  # Redirect to home or another page

        # Fetch the patient and services
        patient = get_object_or_404(Patient, id=patient_id)
        services = Service.objects.all()

        return render(request, 'invoice_form.html', {
            'patient': patient,
            'services': services,
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
        patient_id = request.POST.get('patient_id')
        selected_service_ids = request.POST.getlist('services')
        quantities = request.POST.getlist('quantities')

        # Ensure quantities list is valid
        if not selected_service_ids:
            return JsonResponse({'error': 'No services selected'}, status=400)

        if len(quantities) < len(selected_service_ids):
            return JsonResponse({'error': 'Missing quantities for some services'}, status=400)

        patient = get_object_or_404(Patient, id=patient_id)

        with transaction.atomic():
            # Create the quotation
            quotation = Quotation.objects.create(patient=patient, status='draft')

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

    return render(request, 'create_quotation.html', {
        'patients': patients,
        'services': services,
    })

def quotation_detail(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    return render(request, 'quotation_detail.html', {'quotation': quotation})


def download_quotation_pdf(request, quotation_id):
    """
    Generate and download a quotation PDF that matches the provided image design.
    """
    quotation = get_object_or_404(Quotation, id=quotation_id)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 40px; }}
            .header {{ display: flex; justify-content: space-between; align-servicess: center; }}
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
                <p>Street Address, Zip Code</p>
                <p>Phone Number</p>
            </div>
            <div>
                <strong>Quote to:</strong>
                <p>{escape(quotation.patient.first_name)}</p>
                <p>{escape(quotation.patient.address)}</p>
                <p>{escape(quotation.patient.phone)}</p>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>services</th>
                    <th>Rate</th>
                    <th>Quantity</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
    """
    
  
    html_content += f"""
            </tbody>
        </table>
        <div class="total-section">
            <p>Subtotal: K{quotation.total_amount:.2f}</p>
            <p>Discount: K </p>
            <p>Tax: K 0.00</p>
        </div>
        <div class="grand-total">
            Total: K{quotation.total_amount:.2f}
        </div>
    </body>
    </html>
    """

    pdf_response = HttpResponse(content_type='application/pdf')
    pdf_response['Content-Disposition'] = f'attachment; filename="Quotation_{quotation.id}.pdf"'
    HTML(string=html_content).write_pdf(pdf_response)
    return pdf_response



    return response
def quotation_list(request):
    quotations = Quotation.objects.all()
    return render(request, 'quotation_list.html', {'quotations': quotations})



def exist_patient_appointment(request, patient_id):
    patient = Patient.objects.get(id=patient_id)
    services = Service.objects.filter(name__isnull=False, price__isnull=False)
    return render(request, 'existing_patient_appointment.html', {'patient': patient, 'services': services})






def full_payment_form(request):
    return render(request, 'full_payment_form.html')

def make_full_payment(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    return render(request, 'full_payment_form.html', {
        'invoice': invoice
    })



def full_payment(request):
    if request.method == 'POST':
        invoice_id = request.POST.get('invoice_id')
        patient_id = request.POST.get('patient_id')
        balance = request.POST.get('balance')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id')
        notes = request.POST.get('notes')

        #print out all the fiels
        print(f"Invoice ID: {invoice_id}")
        print(f"Balance: {balance}")
        print(f"Amount: {amount}")
        print(f"Payment Method: {payment_method}")
        print(f"Transaction ID: {transaction_id}")
        print(f"Notes: {notes}")

        # Validate the transaction ID if payment method is not cash
        if payment_method != 'Cash' and not transaction_id:
            messages.error(request, 'Transaction ID is required for non-cash payments.')
            return redirect('full_payment_form')

        # Validate required fields
        if not all([invoice_id, amount, payment_method, patient_id]):
            messages.error(request, 'Missing required fields.')
            return redirect('full_payment_form')
        elif float(amount) < float(balance):
            messages.error(request, 'Payment amount is less then the balance.')
            return redirect('full_payment_form')

        # Fetch the invoice
        invoice = get_object_or_404(Invoice, id=invoice_id)

        # Create the payment
        payment = Payment(
            invoice=invoice,
            patient=invoice.patient,
            amount=amount,
            payment_method=payment_method,
            transaction_id=transaction_id,
            notes=notes,
            status='completed',
            #request.user  # Assuming you want to track who processed the payment
            processed_by=request.user

        )
        payment.save()

        # Update the invoice status
        invoice.status = 'paid'
        invoice.save()

        messages.success(request, 'Payment made successfully!')
        return redirect('invoice_list')

def partial_payment_form(request):
   return(request, 'partial_payment_form.html')

@login_required
def make_partial_payment(request, invoice_id):
    # Fetch the invoice
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    # Calculate the total payments made for the invoice
    total_payments = Payment.objects.filter(invoice=invoice).aggregate(total=Sum('amount'))['total'] or 0

    # Calculate the remaining balance
    remaining_balance = invoice.total_amount - total_payments

    if remaining_balance <= 0:
        messages.error(request, 'Invoice is already fully paid.')
        #Change the status to paid
        invoice.status = 'paid'
        invoice.save()
        # Redirect to the invoice list or detail page
        return redirect('invoice_list')

    # Render the partial payment page with the remaining balance
    return render(request, 'partial_payment_form.html', {
        'invoice': invoice,
        'remaining_balance': remaining_balance
    })

@login_required
def partial_payment(request):
    if request.method == 'POST':
        # Extract form data
        invoice_id = request.POST.get('invoice_id')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id')
        notes = request.POST.get('notes')

        # Validate required fields
        if not all([invoice_id, amount, payment_method]):
            messages.error(request, 'Invoice ID, amount, and payment method are required.')
            return redirect('partial_payment_form')

        try:
            # Convert amount to Decimal
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")
        except (InvalidOperation, ValueError) as e:
            messages.error(request, f'Invalid amount: {str(e)}')
            return redirect('partial_payment_form')

        # Validate payment method
        valid_payment_methods = ['Cash', 'Card', 'Mobile Money']
        if payment_method not in valid_payment_methods:
            messages.error(request, 'Invalid payment method.')
            return redirect('partial_payment_form')

        # Validate transaction ID for non-cash payments
        if payment_method != 'Cash' and not transaction_id:
            messages.error(request, 'Transaction ID is required for non-cash payments.')
            return redirect('partial_payment_form')

        # Fetch the invoice
        try:
            invoice = get_object_or_404(Invoice, id=invoice_id)
        except Exception as e:
            messages.error(request, f'Error fetching invoice: {str(e)}')
            return redirect('partial_payment_form')

        # Calculate remaining balance
        total_payments = invoice.get_total_payments()
        remaining_balance = invoice.total_amount - total_payments

        # Ensure the payment amount does not exceed the remaining balance
        if amount > remaining_balance:
            messages.error(request, 'Payment amount exceeds the remaining balance.')
            return redirect('partial_payment_form')

        # Create the partial payment
        try:
            partial_payment = Payment.objects.create(
                invoice=invoice,
                patient=invoice.patient,
                amount=amount,
                payment_method=payment_method,
                transaction_id=transaction_id,
                notes=notes,
                status='partial',
                processed_by=request.user
            )
        except Exception as e:
            messages.error(request, f'Error creating payment: {str(e)}')
            return redirect('partial_payment_form')

        # Update the invoice status
        total_payments_after_payment = total_payments + amount
        remaining_balance_after_payment = invoice.total_amount - total_payments_after_payment

        if remaining_balance_after_payment <= 0:
            invoice.status = 'paid'
        else:
            invoice.status = 'partially paid'

        invoice.save()

        # Success message
        messages.success(request, 'Partial payment made successfully!')
        return redirect('invoice_list')

    # Handle GET requests (if applicable)
    return redirect('partial_payment_form')



def calendar_view(request):
    today = timezone.now()

    # Fetch appointments for current month
    appointments = Appointment.objects.filter(
        date_time__year=today.year,
        date_time__month=today.month
    ).order_by('date_time')

    # Group appointments by day using defaultdict
    from collections import defaultdict
    grouped = defaultdict(list)
    for appt in appointments:
        grouped[appt.date_time.day].append(appt)

    # Generate all days in the current month
    _, days_in_month = calendar.monthrange(today.year, today.month)
    month_days = list(range(1, days_in_month + 1))

    # Create a list of dicts: {'day': 5, 'appointments': [...]}
    days_with_appointments = [
        {
            'day': day,
            'appointments': grouped.get(day, [])
        }
        for day in month_days
    ]

    # Pass weekday labels and other data
    week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    return render(request, 'calendar.html', {
        'today': today,
        'days_with_appointments': days_with_appointments,
        'week_days': week_days,
        'current_month': today.strftime("%B %Y")
    })



@login_required
def inventory_dashboard(request):
    low_stock_items = InventoryItem.objects.filter(quantity__lte=models.F('reorder_level'))
    recent_transactions = InventoryTransaction.objects.all().order_by('-timestamp')[:5]
    
    context = {
        'low_stock_items': low_stock_items,
        'recent_transactions': recent_transactions
    }
    return render(request, 'inventory_dashboard.html', context)

@login_required
def item_list(request):
    items = InventoryItem.objects.all()
    return render(request, 'item_list.html', {'items': items})

@login_required
def item_detail(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    transactions = item.transactions.all().order_by('-timestamp')[:10]
    return render(request, 'item_detail.html', {
        'item': item,
        'transactions': transactions
    })

@login_required
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('item_list')
    else:
        form = ItemForm()
    return render(request, 'forms.html', {'form': form, 'title': 'Add New Item'})




@login_required
def item_update(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Item '{form.cleaned_data['name']}' updated successfully")
            return redirect('item_detail', pk=item.pk)
    else:
        form = InventoryItemForm(instance=item)
    
    return render(request, 'item_form.html', {
        'form': form, 
        'item': item,
        'title': f'Edit {item.name}'
    })

@login_required
def item_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    
    if request.method == 'POST':
        item_name = item.name
        item.delete()
        messages.success(request, f"Item '{item_name}' has been deleted")
        return redirect('item_list')
    
    return render(request, 'item_confirm_delete.html', {
        'item': item,
        'title': f'Delete {item.name}'
    })

@login_required
def item_transactions(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    transactions = item.transactions.all().order_by('-timestamp')
    
    return render(request, 'item_transactions.html', {
        'item': item,
        'transactions': transactions,
        'title': f'{item.name} - Transactions'
    })


@login_required
def transaction_create(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, item=item)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.item = item
            transaction.user = request.user
            
            try:
                # Handle transaction logic
                if transaction.transaction_type == 'OUT' and transaction.quantity > item.quantity:
                    messages.error(request, "Cannot remove more items than available in stock")
                    return render(request, 'transaction_form.html', {
                        'form': form,
                        'item': item,
                        'title': 'Add Transaction'
                    })
                
                transaction.save()
                
                # Update item quantity
                if transaction.transaction_type == 'IN':
                    item.quantity += transaction.quantity
                elif transaction.transaction_type == 'OUT':
                    item.quantity -= transaction.quantity
                    
                item.save(update_fields=['quantity', 'last_updated'])
                
                messages.success(
                    request, 
                    f"{transaction.get_transaction_type_display()} of {transaction.quantity} units recorded"
                )
                
                return redirect('inventory:item_detail', pk=item.pk)
                
            except Exception as e:
                messages.error(request, f"Error recording transaction: {str(e)}")
                return render(request, 'transaction_form.html', {
                    'form': form,
                    'item': item,
                    'title': 'Add Transaction'
                })
    else:
        form = TransactionForm(item=item)
    
    return render(request, 'transaction_form.html', {
        'form': form,
        'item': item,
        'title': 'Add Transaction'
    })

    return render(request, 'supplier_form.html', {
        'form': form,
        'title': 'Add New Supplier'
    })


@login_required
def category_list(request):
    return render(request, 'item_category_list.html', {
        'categories': ItemCategory.objects.all().order_by('name'),
        'title': 'Item Categories'
    })

@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{form.cleaned_data['name']}' created successfully")
            return redirect('category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'supplier_category_form.html', {
        'form': form,
        'title': 'Add New Category'
    })

@login_required
def category_update(request, pk):
    category = get_object_or_404(ItemCategory, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{form.cleaned_data['name']}' updated successfully")
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'supplier_category_form.html', {
        'form': form,
        'title': f'Edit {category.name}',
        'category': category
    })

@login_required
def category_delete(request, pk):
    category = get_object_or_404(ItemCategory, pk=pk)
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f"Category '{category_name}' deleted successfully")
        return redirect('category_list')
    
    return render(request, 'supplier_category_delete.html', {
        'object': category,
        'title': f'Delete {category.name}',
        'type': 'category'
    })

@login_required
def supplier_list(request):
    return render(request, 'supplier_list.html', {
        'suppliers': Supplier.objects.all().order_by('name'),
        'title': 'Suppliers'
    })

@login_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Supplier '{form.cleaned_data['name']}' created successfully")
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    
    return render(request, 'supplier_category_form.html', {
        'form': form,
        'title': 'Add New Supplier'
    })

@login_required
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f"Supplier '{form.cleaned_data['name']}' updated successfully")
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    
    return render(request, 'supplier_category_form.html', {
        'form': form,
        'title': f'Edit {supplier.name}',
        'supplier': supplier
    })

@login_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier_name = supplier.name
        supplier.delete()
        messages.success(request, f"Supplier '{supplier_name}' deleted successfully")
        return redirect('supplier_list')
    
    return render(request, 'supplier_category_delete.html', {
        'object': supplier,
        'title': f'Delete {supplier.name}',
        'type': 'supplier'
    })


def turn_invoice_to_receipt(request, invoice_id):
    """
    Converts an existing Invoice into a Receipt.
    Copies all details from the Invoice to the Receipt without modifications.
    """
    # Fetch the Invoice and related Payment records
    invoice = get_object_or_404(Invoice, id=invoice_id)
    payments = Payment.objects.filter(invoice=invoice)

    try:
        with transaction.atomic():
            # Create the Receipt object
            receipt = Receipt.objects.create(
                invoice=invoice,
                payment=payments.first(),  # Link the first payment (or handle multiple payments as needed)
                patient=invoice.patient,
                branch=invoice.branch,  # Copy the branch from the Invoice
                total_amount=invoice.total_amount,
                notes=invoice.notes,  # Copy notes from the Invoice
            )

            # Generate a unique receipt number
            receipt.receipt_number = f"RECEIPT-{uuid.uuid4().hex[:8]}"
            receipt.save()

            # Copy InvoiceService details to ReceiptItem
            for invoice_service in invoice.invoiceservice_set.all():
                ReceiptItem.objects.create(
                    receipt=receipt,
                    item=invoice_service.service,  # Assuming service is treated as an item
                    price=invoice_service.price_at_time,
                    quantity=invoice_service.quantity
                )

            # Optionally mark the Invoice as paid if fully paid
            if invoice.status == 'paid':
                messages.success(request, "The invoice has been successfully converted into a receipt.")
            else:
                messages.warning(request, "The invoice was partially converted into a receipt.")

    except Exception as e:
        # Handle any unexpected errors during the process
        messages.error(request, f"Failed to create the receipt: {str(e)}")
        return redirect('invoice_list')  # Redirect to the list of invoices

    # Add a success message
    messages.success(request, "The invoice has been successfully converted into a receipt.")

    # Redirect to the receipt detail page
    return redirect('receipt_detail', receipt_id=receipt.id)



def download_invoice_pdf(request, invoice_id):
    # Fetch the invoice object
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Fetch related services for the invoice
    invoice_services = InvoiceService.objects.filter(invoice=invoice)

    # Start building the HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 40px; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; }}
            .header img {{ width: 100px; }}
            .invoice-title {{ background-color: #00A9CE; color: white; font-size: 24px; padding: 10px; text-align: center; font-weight: bold; }}
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
                <h2>Superior Dental Solutions Limited</h2>
            </div>

            <div>
                <p>Invoice Number: {invoice.id}</p>
                <p>Total Amount Due:</p>
                <p>K{invoice.total_amount:.2f}</p>
                <p>Due Date:</p>
                <p>Not specified</p>
            </div>
        </div>
        <div class="invoice-title">INVOICE</div>
        <div class="details">
            <div>
                <strong>Invoice from:</strong>
                <p>Superior Dental Solution Limited</p>
                <p>Street Address, Zip Code</p>
                <p>Phone Number</p>
            </div>
            <div>
                <strong>Invoice to:</strong>
                <p>{escape(invoice.patient.first_name)} {escape(invoice.patient.last_name)}</p>
                <p>{escape(invoice.patient.address)}</p>
                <p>{escape(invoice.patient.phone)}</p>
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
    # Populate the table with services
    for service in invoice_services:
        html_content += f"""
                <tr>
                    <td>{escape(service.service.name)}</td>
                    <td>{service.price_at_time}</td>
                    <td>{service.quantity}</td>
                    <td>K{service.price_at_time * service.quantity:.2f}</td>
                </tr>
        """
    html_content += """
            </tbody>
        </table>
        <div class="total-section">
            <p>Subtotal: K{:.2f}</p>
            <p>Discount: K{:.2f}</p>
            <p>Tax: K{:.2f}</p>
        </div>
        <div class="grand-total">
            Total: K{:.2f}
        </div>
    </body>
    </html>
    """.format(
        invoice.total_amount,  # Subtotal
        0.00,  # Discount
        0.00,  # Tax
        invoice.total_amount  # Total
    )
    # Generate the PDF response
    pdf_response = HttpResponse(content_type='application/pdf')
    pdf_response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.id}.pdf"'
    HTML(string=html_content).write_pdf(pdf_response)
    return pdf_response


@login_required
def receipt_list(request):
    receipts = Receipt.objects.all().select_related('patient', 'invoice')
    return render(request, 'receipt_list.html', {'receipts': receipts})

@login_required
def receipt_detail(request, pk):
    # Fetch the receipt object using the provided primary key (pk)
    receipt = get_object_or_404(Receipt, id=pk)
    
    # Fetch the associated invoice (if any)
    invoice = getattr(receipt, 'invoice', None)  # Safely access the invoice attribute
    
    # Check if the invoice exists
    if not invoice:
        messages.error(request, "No associated invoice found for this receipt.")
        return redirect('receipt_list')  # Redirect to the receipt list page
    
    # Calculate subtotal from the invoice's total amount
    subtotal = invoice.total_amount or Decimal('0.00')
    
    # Render the receipt details template
    return render(request, 'receipt_detail.html', {
        'receipt': receipt,
        'invoice': invoice,
        'subtotal': subtotal,
    })


def receipt_detail_view(request, receipt_id):
    """
    Displays the details of a specific receipt and provides a download button.
    """
    # Fetch the receipt and its associated items
    receipt = get_object_or_404(Receipt, id=receipt_id)
    receipt_items = ReceiptItem.objects.filter(receipt=receipt)

    # Render the receipt detail page
    return render(request, 'receipt_detail.html', {
        'receipt': receipt,
        'receipt_items': receipt_items,
    })

def download_receipt_pdf(request, receipt_id):
    """
    Generates and downloads a PDF version of the receipt.
    """
    # Fetch the receipt and its associated items
    receipt = get_object_or_404(Receipt, id=receipt_id)
    receipt_items = ReceiptItem.objects.filter(receipt=receipt)

    # Render the HTML content for the PDF
    html_content = render_to_string('receipt_pdf.html', {
        'receipt': receipt,
        'receipt_items': receipt_items,
    })

    # Generate the PDF response
    pdf_response = HttpResponse(content_type='application/pdf')
    pdf_response['Content-Disposition'] = f'attachment; filename="Receipt_{receipt.receipt_number}.pdf"'
    HTML(string=html_content).write_pdf(pdf_response)

    return pdf_response\
    

