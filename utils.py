import string
import random 

def generate_tracking_number(prifix="LGX", length=6)->str:
    chars = string.ascii_uppercase + string.digits
    code = "".join(random.choices(chars, k=length))
    return f"{prifix}-{code}"


