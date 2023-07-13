from django import forms


class ImagePromptForm(forms.Form):
    prompt = forms.CharField(
        widget=forms.Textarea(attrs={"rows": "3"}), help_text="E.g. 'A pegasus in space in the style of tron'"
    )
