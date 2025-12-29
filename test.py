import random
import re


CITIES = [
    ("Ahmedabad", "Gujarat", 380001),
    ("Surat", "Gujarat", 395003),
    ("Vadodara", "Gujarat", 390001),
    ("Jaipur", "Rajasthan", 302001),
    ("Udaipur", "Rajasthan", 313001),
    ("Delhi", "Delhi", 110001),
    ("Mumbai", "Maharashtra", 400001),
    ("Pune", "Maharashtra", 411001),
    ("Bengaluru", "Karnataka", 560001),
    ("Hyderabad", "Telangana", 500001),
    ("Chennai", "Tamil Nadu", 600001),
    ("Kolkata", "West Bengal", 700001),
]


city, state, pincode = random.choice(CITIES)

address = f"{random.randint(100, 999)} {random.choice(['Main St', '2nd St', '3rd St', 'Park Ave', 'Oak St'])}, {city}, {state} - {pincode}"

address_word = re.findall(r'\w+', address)
city, state, pincode = address_word[-3], address_word[-2], int(address_word[-1])
print("city:", city)
print("state:", state)
print("pincode:", pincode)