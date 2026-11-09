import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Order


class SignupForm(UserCreationForm):
    password1 = forms.CharField(
        label='Пароль',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    password2 = None


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['full_name', 'phone', 'delivery', 'address', 'comment']
        widgets = {'comment': forms.Textarea(attrs={'rows': 3})}
    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if not 10 <= len(re.sub(r'\D', '', phone)) <= 15:
            raise forms.ValidationError('Введите телефон: от 10 до 15 цифр.')
        return phone
    def clean(self):
        data = super().clean()
        if data.get('delivery') == 'courier' and not data.get('address'):
            self.add_error('address', 'Укажите адрес доставки.')
        return data
