from django.shortcuts import render,redirect

# Create your views here.
from django.views.generic import View,FormView,CreateView
from student.forms import StudentCreateForm,LoginForm
from django.urls import reverse_lazy
from django.contrib.auth import authenticate,login,logout
from instructor.models import Course,Cart,Order,Module,Lesson
import razorpay


from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator 

from student.decorators import signin_required

from decouple import config

RZP_KEY_ID=config("RZP_KEY_ID")

RZP_KEY_SECRET=config("RZP_KEY_SECRET")


class StudentRegistrationView(CreateView):

    template_name="student_register.html"

    form_class=StudentCreateForm
    
    success_url=reverse_lazy("signin")
        
class SignInView(FormView):

    template_name="signin.html"

    form_class=LoginForm

    def post(self,request,*args,**kwargs):

        form_data=request.POST

        form_instance=LoginForm(form_data)

        if form_instance.is_valid():

            data=form_instance.cleaned_data

            uname=data.get("username")

            pwd=data.get("password")

            user_instance=authenticate(request,username=uname,password=pwd)

            if user_instance:

                login(request,user_instance)

                if user_instance.role=="Student":

                    return redirect("index")
                
                else:

                    return render(request,self.template_name,{"form":form_instance})

@method_decorator(signin_required,name='dispatch')            
class IndexView(View):

    def get(self,request,*args,**kwargs):

        all_courses=Course.objects.all()

        # purchased_courses=request.user.purchase.all()
        purchased_courses=Order.objects.filter(student=request.user).values_list("course_objects",flat=True)

        print("**********************",purchased_courses)

        return render(request,"index.html",{"courses":all_courses,"purchased_courses":purchased_courses})


@method_decorator(signin_required,name='dispatch')  
class CourseDetailView(View):

    def get(self,request,*args,**kwargs):

        id=kwargs.get("pk")

        course_instance=Course.objects.get(id=id)

        return render (request,"course_detail.html",{"course":course_instance})    


@method_decorator(signin_required,name='dispatch')  
class AddToCartView(View):

    def get(self,request,*args,**kwargs):

        id=kwargs.get("pk")

        course_instance=Course.objects.get(id=id)

        user_instance=request.user

        cart_instance,created=Cart.objects.get_or_create(course_object=course_instance,user=user_instance)

        print(created,"****************************************")

        return redirect("index")    

#cart summary view
from django.db.models import Sum

@method_decorator(signin_required,name='dispatch')  
class CartSummaryView(View):

    def get(self,request,*args,**kwargs):

        qs=request.user.basket.all()

        cart_total=qs.values("course_object__price").aggregate(total=Sum("course_object__price")).get("total")

        print("*****************",cart_total)

        return render(request,"cart_summary.html",{"carts":qs,"basket_total":cart_total})    
    
    
#cart item delete
@method_decorator(signin_required,name='dispatch')  
class CartItemDeleteView(View):

    def get(self,request,*args,**kwargs):

        id=kwargs.get("pk")

        cart_instance=Cart.objects.get(id=id)

        if cart_instance.user != request.user:

            return redirect("index")

        Cart.objects.get(id=id).delete()

        return redirect("cart-summary")    
    

#check out
@method_decorator(signin_required,name='dispatch')  
class CheckOutView(View):

    def get(self,request,*args,**kwrags):

        cart_items=request.user.basket.all()

        order_total=sum([ci.course_object.price for ci in cart_items])

        order_instance=Order.objects.create(student=request.user)

        for ci in cart_items:

            order_instance.course_objects.add(ci.course_object)

            ci.delete()

        order_instance.save()

        if order_total>0:

            client = razorpay.Client(auth=("rzp_test_LfKQOBZEN0YN7v", "KWlX6MJBfAAWiBharco9JYqi"))

            data = { "amount": int(order_total*100), "currency": "INR", "receipt": "order_rcptid_11" }

            payment = client.order.create(data=data) 

            rzp_id=payment.get("id")

            order_instance.rzp_order_id=rzp_id

            order_instance.save()

            context={
                "rzp_key_id":RZP_KEY_ID,
                "amount":int(order_total*100),
                "rzp_order_id":rzp_id
            }

            return render(request,"payment.html",context)  
        
        elif order_total==0:

            order_instance.is_paid=True

            order_instance.save()

        return redirect("mycourses")  
    

#mycourses   

@method_decorator(signin_required,name='dispatch')  
class MyCoursesView(View):

     def get(self,request,*args,**kwargs):
         
         qs=request.user.purchase.filter(is_paid=True)

         return render(request,'mycourses.html',{"orders":qs})

#lesson detail
@method_decorator(signin_required,name='dispatch')  
class LessonDetailView(View):

    def get(self,request,*args,**kwargs):

        course_id=kwargs.get("pk")

        course_instance=Course.objects.get(id=course_id)

        puchased_courses=request.user.purchase.filter(is_paid=True).values_list("course_objects",flat=True)

        print(puchased_courses,"-------------------")

        if course_instance.id not in puchased_courses:

            return redirect("index")

        module_id=request.GET.get("module") if "module" in request.GET else course_instance.modules.first().id

        module_instance=Module.objects.get(id=module_id,course_object=course_instance)

        lesson_id=request.GET.get("lesson") if "lesson" in request.GET else module_instance.lessons.first().id

        lesson_instance=Lesson.objects.get(id=lesson_id,module_object=module_instance)

        return render(request,"lesson_detail.html",{"course":course_instance,"lesson":lesson_instance})
    
#payemnt verification
# 
 


@method_decorator([csrf_exempt],name="dispatch")    
class PaymentVerificationView(View):

    def post(self,request,*args,**kwargs):

        print(request.POST,"*******************")\
        
        client=razorpay.Client(auth=(RZP_KEY_ID,RZP_KEY_SECRET))

        try:
            client.utility.verify_payment_signature(request.POST)

            print("payment success")

            rzp_order_id=request.POST.get("razorpay_order_id")

            order_instance=Order.objects.get(rzp_order_id=rzp_order_id)

            order_instance.is_paid=True

            order_instance.save()

            login(request,order_instance.student)

        except:

            print("payment failed")    

        return redirect("index")    

#logout

@method_decorator(signin_required,name='dispatch')  
class SignOutView(View):

    def get(self,request,*args,**kwargs):

        logout(request)

        return redirect("signin")