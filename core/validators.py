from django.core.validators import RegexValidator

name_validator = RegexValidator(
    regex=r"^[A-Za-z0-9][A-Za-z0-9' -]*$",
    message="Only letters, numbers, spaces, hyphens and apostrophes are allowed."
)

# Phone numbers are stored WITHOUT the country code — exactly 10 digits.
# The country code is stored separately alongside it.
phone_validator = RegexValidator(
    regex=r"^[0-9]{10}$",
    message="Enter a valid 10-digit phone number (no spaces, no country code)."
)

alnum_id_validator = RegexValidator(
    regex=r"^[A-Za-z0-9-]+$",
    message="Only letters, numbers and hyphens are allowed."
)

bank_account_validator = RegexValidator(
    regex=r"^[0-9]{9,18}$",
    message="Bank account number must be 9 to 18 digits."
)

ifsc_validator = RegexValidator(
    regex=r"^[A-Za-z]{4}0[A-Za-z0-9]{6}$",
    message="Enter a valid IFSC code, e.g. HDFC0001234."
)

pan_validator = RegexValidator(
    regex=r"^[A-Za-z]{5}[0-9]{4}[A-Za-z]$",
    message="Enter a valid PAN number, e.g. ABCDE1234F."
)

aadhar_validator = RegexValidator(
    regex=r"^[0-9]{12}$",
    message="Aadhar number must be exactly 12 digits."
)
numeric_validator = RegexValidator(
    regex=r"^[0-9]*$",
    message="Only digits are allowed."
)
   


# Country codes offered on every phone number field in the app.
# India is listed first since it's the primary country for this HRMS.
COUNTRY_CODES = [
    ('+91', 'India (+91)'),
    ('+1', 'USA / Canada (+1)'),
    ('+44', 'UK (+44)'),
    ('+61', 'Australia (+61)'),
    ('+971', 'UAE (+971)'),
    ('+65', 'Singapore (+65)'),
    ('+49', 'Germany (+49)'),
    ('+33', 'France (+33)'),
    ('+81', 'Japan (+81)'),
    ('+86', 'China (+86)'),
    ('+92', 'Pakistan (+92)'),
    ('+880', 'Bangladesh (+880)'),
    ('+94', 'Sri Lanka (+94)'),
    ('+966', 'Saudi Arabia (+966)'),
    ('+974', 'Qatar (+974)'),
]