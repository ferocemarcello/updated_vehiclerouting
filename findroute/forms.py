from django import forms

class UploadFileForm(forms.Form):
    file_field = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': False}))
    def __init__(self,label=None, *args, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)
        if label:
            self.fields['file_field'].label=label
class CheckMultiCheckBox(forms.Form):
    '''(attrs={'class' : 'form-control'})'''
    routeselection = forms.MultipleChoiceField(label="Select Routes to show",widget=forms.CheckboxSelectMultiple,
                                               choices=[])
    def __init__(self,routechoices=None, *args, **kwargs):
        super(CheckMultiCheckBox, self).__init__(*args, **kwargs)
        if routechoices:
            self.fields['routeselection'].widget.attrs['size'] = '30'
            self.fields['routeselection'].choices = routechoices
            self.fields['routeselection'].initial=[x[0] for x in self.fields['routeselection'].choices]
class HereApiForm(forms.Form):
    here_app_id= forms.CharField(label='Here App id:',max_length=30,required=True)
    here_app_code= forms.CharField(label='Here App code:', max_length=30,required=True)
