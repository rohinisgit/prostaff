from django import template

register = template.Library()

@register.filter
def add_error_class(field):
    """Renders a bound field with an 'is-invalid' class appended when it
    has validation errors, so the input border actually turns red instead
    of only showing a generic banner at the top of the form."""
    existing = field.field.widget.attrs.get('class', '')
    css_class = f"{existing} is-invalid".strip() if field.errors else existing
    return field.as_widget(attrs={'class': css_class})