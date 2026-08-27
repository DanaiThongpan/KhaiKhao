from django import forms
from .models import Product, ProductCategory

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'code', 'name', 'description', 'cost_price', 'selling_price', 'stock_quantity', 'min_stock', 'unit', 'image', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ตกแต่ง CSS ให้กล่อง input ทุกตัว
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class CategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'is_active']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'